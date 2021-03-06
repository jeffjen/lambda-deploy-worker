from __future__ import print_function
from datetime import datetime

import boto3
import botocore
import json
import os
import subprocess
import time

from config import config

s3 = boto3.resource("s3")
sns = boto3.client("sns")

# Local cache tag map
cache = {}

def deploy(event, context):
    msg = json.loads(event["Records"][0]["Sns"]["Message"])

    # Target to deploy
    target = msg["Instance"]["PublicIpAddress"]

    # Target belongs to ClusterName group
    clusterName = msg["ClusterName"]

    # Obtain Runtime Service Specification
    spec = msg["ContainerSpec"]

    specfile = "/tmp/{Key}".format(**spec)
    specdir = os.path.dirname(specfile)
    # Setup directory for Specification
    if not os.path.exists(specdir):
        os.makedirs(specdir)

    # Obtain cached version of said Specification
    version = cache.get(spec["Key"], "")

    # Get the object and must be newer then local one
    try:
        obj = s3.Object(spec["Bucket"], spec["Key"]).get(IfNoneMatch=version)
        with open(specfile, "w+") as f:
            f.write(obj["Body"].read())
        cache[spec["Key"]] = obj["ETag"]
    except botocore.exceptions.ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 304:
            pass
        else:
            raise

    # Invoke docker-compose to proces the Service Specification
    args = [ "./deploy-worker", "--cluster", clusterName, "--public-ip", target, "--spec", specfile ]
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    for line in proc.stdout:
        print(line)

    # Wait for the process to finish, and check child exit status
    while proc.poll() is None:
        time.sleep(1)
    if proc.returncode != 0:
        raise RuntimeError("Unable to deploy with requested parameter")

    # Finally report that the deployment was successful
    msg["Status"] = "Complete"
    msg["Timestamp"] = datetime.now().isoformat()
    sns.publish(TopicArn=config["REPORT_TOPIC_ARN"], Message=json.dumps(msg, indent=2))
