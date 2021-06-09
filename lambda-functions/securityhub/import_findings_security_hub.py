"""
 Imports finding in Security Hub and upload the reports to S3 
 Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 SPDX-License-Identifier: MIT-0
"""

import os
import json
import logging
import boto3
import securityhub
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

FINDING_TITLE = "CodeAnalysis"
FINDING_DESCRIPTION_TEMPLATE = "Summarized report of code scan with {0}"
FINDING_TYPE_TEMPLATE = "{0} code scan"
BEST_PRACTICES_OWASP = "https://owasp.org/www-project-top-ten/"
report_url = "https://aws.amazon.com"

def process_message(event):
    """ Process Lambda Event """
    if event['messageType'] == 'CodeScanReport':
        account_id = boto3.client('sts').get_caller_identity().get('Account')
        region = os.environ['AWS_REGION']
        created_at = event['createdAt']
        source_repository = event['source_repository']
        source_branch = event['source_branch']
        source_commitid = event['source_commitid']
        build_id = event['build_id']
        report_type = event['reportType']
        finding_type = FINDING_TYPE_TEMPLATE.format(report_type)
        generator_id = f"{report_type.lower()}-{source_repository}-{source_branch}"
        
        ## S3 버켓 업로드
        s3 = boto3.client('s3')
        s3bucket = "myfirstbucket"
        key = f"reports/{event['reportType']}/{build_id}-{created_at}.json"
        s3.put_object(Bucket=s3bucket, Body=json.dumps(event), Key=key, ServerSideEncryption='aws:kms')
        report_url = f"https://s3.console.aws.amazon.com/s3/object/{s3bucket}/{key}?region={region}"
                
        ## OWASP SCA report 파싱
        if event['reportType'] == 'OWASP-Dependency-Check':
            severity = 50
            FINDING_TITLE = "OWASP Dependecy Check Analysis"
            dep_pkgs = len(event['report']['dependencies'])
            for i in range(dep_pkgs):
                if "packages" in event['report']['dependencies'][i]:
                    confidence = event['report']['dependencies'][i]['packages'][0]['confidence']
                    url = event['report']['dependencies'][i]['packages'][0]['url']
                    finding_id = f"{i}-{report_type.lower()}-{build_id}"
                    finding_description = f"Package: {event['report']['dependencies'][i]['packages'][0]['id']}, Confidence: {confidence}, URL: {url}"
                    created_at = datetime.now(timezone.utc).isoformat()
                    ### normalized_severity 값 설정
                    if confidence == "HIGHEST":
                        normalized_severity = 80
                    else:
                        normalized_severity = 50
                    ### Securityhub post 호출
                    securityhub.import_finding_to_sh(i, account_id, region, created_at, source_repository, source_branch, source_commitid, build_id, report_url, finding_id, generator_id, normalized_severity, severity, finding_type, FINDING_TITLE, finding_description, BEST_PRACTICES_OWASP)

        ### SonarQube SAST report 파싱
        elif event['reportType'] == 'SONAR-QUBE':           
            severity = 50
            FINDING_TITLE = "SonarQube StaticCode Analysis"         
            report_count = event['report']['total']
            for i in range(report_count):
                finding_id = f"{i}-{report_type.lower()}-{source_repository}-{source_branch}-{build_id}"
                finding_description = f"{event['report']['issues'][i]['type']}-{event['report']['issues'][i]['message']}-{i}, component: {event['report']['issues'][i]['component']}"
                created_at = datetime.now(timezone.utc).isoformat()
                report_severity = event['report']['issues'][i]['severity']
                ### normalized_severity 값 설정
                if report_severity == 'MAJOR':
                    normalized_severity = 70
                elif report_severity == 'BLOCKER':
                    normalized_severity = 90
                elif report_severity == 'CRITICAL':
                    normalized_severity = 90
                else:
                    normalized_severity= 20
                ### Securityhub post 호출
                securityhub.import_finding_to_sh(i, account_id, region, created_at, source_repository, source_branch, source_commitid, build_id, report_url, finding_id, generator_id, normalized_severity, severity, finding_type, FINDING_TITLE, finding_description, BEST_PRACTICES_OWASP)
        
        ### OWASP Zap DAST report 파싱
        elif event['reportType'] == 'OWASP-Zap':
            severity = 50
            FINDING_TITLE = "OWASP ZAP DynamicCode Analysis"
            alert_ct = event['report']['Report']['Sites']['Alerts']['AlertItem']
            alert_count = len(alert_ct)
            for alertno in range(alert_count):
                risk_desc = event['report']['Report']['Sites']['Alerts']['AlertItem'][alertno]['RiskDesc']
                riskletters = risk_desc[0:3]
                ### normalized_severity 값 설정
                if riskletters == 'Hig':
                    normalized_severity = 70
                elif riskletters == 'Med':
                    normalized_severity = 60
                elif riskletters == 'Low' or riskletters == 'Inf':  
                    normalized_severity = 30
                else:
                    normalized_severity = 90                                       
                finding_description = f"{alertno}-Vulerability:{event['report']['Report']['Sites']['Alerts']['AlertItem'][alertno]['Alert']}"
                finding_id = f"{alertno}-{report_type.lower()}-{build_id}"
                created_at = datetime.now(timezone.utc).isoformat()
                ### Securityhub post 호출
                securityhub.import_finding_to_sh(alertno, account_id, region, created_at, source_repository, source_branch, source_commitid, build_id, report_url, finding_id, generator_id, normalized_severity, severity, finding_type, FINDING_TITLE, finding_description, BEST_PRACTICES_OWASP)
        else:
            print("Invalid report type was provided")                
    else:
        logger.error("Report type not supported:")

def lambda_handler(event, context):
    try:
        logger.info("Starting function")
        return process_message(event)
    except Exception as error:
        logger.error("Error {}".format(error))
        raise

