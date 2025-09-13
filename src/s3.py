import boto3
import itertools
import json
import logging

logger = logging.getLogger(__name__)


def with_client(client):
    def outer(fn):
        def inner(*args, **kwargs):
            return fn(*args, **kwargs)

        return inner

    return outer


def get_iam_policies_for_bucket(client, bucket_name: str):
    """
        Retrieve all IAM policies for an account that reference a given bucket
    """
    policies = {}
    for username in get_iam_users(client):
        policies[username] = get_user_policies(client, username, bucket_name)
    return json.dumps(policies)


def get_iam_users(client):
    """
    Retrieve all users for an IAM account
    """
    paginator = client.get_paginator('list_users')
    itr = paginator.paginate(
        PaginationConfig=dict()
    )

    for page in itr:
        for user in page.get('Users', []):
            yield user['UserName']


def get_user_policies(client, username, bucket):
    inline = get_inline_user_policies(client, username)
    attached = get_attached_user_policies(client, username)

    logger.info(f"Getting policies for user {username}, bucket {bucket}")
    logger.info(f"Found {len(inline)} inline policies: {inline}")
    logger.info(f"Found {len(attached)} attached policies: {attached}")

    filtered = []

    # Process inline policies
    for policy_name in inline:
        try:
            res = client.get_user_policy(UserName=username, PolicyName=policy_name)
            policy_doc = res['PolicyDocument']
            if isinstance(policy_doc, str):
                policy_doc = json.loads(policy_doc)

            # Check if policy references the bucket
            found_match = False
            for statement in policy_doc.get('Statement', []):
                if found_match:
                    break

                resource = statement.get('Resource', '')
                if isinstance(resource, list):
                    resources = resource
                else:
                    resources = [resource]

                logger.debug(f"Checking resources for policy {policy_name}: {resources}")

                for res_str in resources:
                    # Handle various resource formats
                    if res_str == '*':
                        # Wildcard matches everything
                        filtered.append({'PolicyName': policy_name, 'PolicyDocument': policy_doc})
                        found_match = True
                        break
                    elif 'arn:aws:s3:::' in res_str:
                        # Standard S3 ARN format: arn:aws:s3:::bucket/* or arn:aws:s3:::bucket
                        if f'arn:aws:s3:::{bucket}' in res_str or 'arn:aws:s3:::*' in res_str:
                            filtered.append({'PolicyName': policy_name, 'PolicyDocument': policy_doc})
                            found_match = True
                            break
                    elif ':' in res_str and 'bucket/' in res_str:
                        # Legacy format with bucket/ prefix
                        parts = res_str.split(':')
                        if len(parts) > 5:
                            resource_part = parts[5]
                            if resource_part.startswith('bucket/'):
                                bucket_name = resource_part.replace('bucket/', '').split('/')[0]
                                if bucket_name == bucket or bucket_name == '*':
                                    filtered.append({'PolicyName': policy_name, 'PolicyDocument': policy_doc})
                                    found_match = True
                                    break
                    elif bucket in res_str:
                        # Simple string match as fallback
                        filtered.append({'PolicyName': policy_name, 'PolicyDocument': policy_doc})
                        found_match = True
                        break
        except Exception as e:
            print(f"Error getting inline policy {policy_name} for user {username}: {e}")

    # Process attached (managed) policies
    for policy_info in attached:
        try:
            policy_arn = policy_info['PolicyArn']
            policy_name = policy_info['PolicyName']

            # Get the policy version
            policy_versions = client.list_policy_versions(PolicyArn=policy_arn)
            default_version = next(v['VersionId'] for v in policy_versions['Versions'] if v['IsDefaultVersion'])

            # Get the policy document
            policy_doc_res = client.get_policy_version(PolicyArn=policy_arn, VersionId=default_version)
            policy_doc = policy_doc_res['PolicyVersion']['Document']
            if isinstance(policy_doc, str):
                policy_doc = json.loads(policy_doc)

            for statement in policy_doc.get('Statement', []):
                resource = statement.get('Resource', '')
                if isinstance(resource, list):
                    resources = resource
                else:
                    resources = [resource]

                for res_str in resources:
                    if ':' in res_str:
                        parts = res_str.split(':')
                        if len(parts) > 5 and parts[5].startswith('bucket/'):
                            bucket_name = parts[5].replace('bucket/', '')
                            if bucket_name == bucket or bucket_name == '*':
                                filtered.append({'PolicyName': policy_name, 'PolicyDocument': policy_doc})
                                break
                    elif res_str == '*' or bucket in res_str:
                        filtered.append({'PolicyName': policy_name, 'PolicyDocument': policy_doc})
                        break
        except Exception as e:
            print(f"Error getting attached policy {policy_name} for user {username}: {e}")

    return filtered


def get_inline_user_policies(client, username: str):
    return client.list_user_policies(UserName=username)['PolicyNames']


def get_attached_user_policies(client, username: str):
    result = client.list_attached_user_policies(UserName=username)
    return result.get('AttachedPolicies', [])
