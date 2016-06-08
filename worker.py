from __future__ import print_function

import boto3
import botocore
import json
import os
import subprocess

s3 = boto3.resource("s3")

# Local cache tag map
cache = {}

def deploy(event, context):
    msg = json.loads(event["Records"][0]["Sns"]["Message"])
    target = msg["Instance"]["PublicIpAddress"]

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
    args = [ "./deploy-worker", "--public-ip", target, "--spec", specfile ]
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    for line in proc.stdout:
        print(line)
