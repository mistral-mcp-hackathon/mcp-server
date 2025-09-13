import boto3
import itertools
import json


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

    filtered = []
    for policy_name in itertools.chain(inline, attached):
        res = client.get_user_policy(UserName=username, PolicyName=policy_name)
        for statement in res['PolicyDocument']['Statement']:
            parts = statement['Resource'].split(':')
            if parts[5].startswith('bucket/'):
                bucket_name = parts[5].replace('bucket/', '')
                if bucket_name == bucket or bucket_name == '*':
                    filtered.append({'PolicyName': policy_name, 'PolicyDocument': res['PolicyDocument']})
                    break
    return filtered


def get_inline_user_policies(client, username: str):
    return client.list_user_policies(UserName=username)['PolicyNames']


def get_attached_user_policies(client, username: str):
    return client.list_attached_user_policies(UserName=username)['AttachedPolicies']
