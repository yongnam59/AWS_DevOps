         ___        ______     ____ _                 _  ___  
        / \ \      / / ___|   / ___| | ___  _   _  __| |/ _ \ 
       / _ \ \ /\ / /\___ \  | |   | |/ _ \| | | |/ _` | (_) |
      / ___ \ V  V /  ___) | | |___| | (_) | |_| | (_| |\__, |
     /_/   \_\_/\_/  |____/   \____|_|\___/ \__,_|\__,_|  /_/ 
 ----------------------------------------------------------------- 

# All AWS DevOps 환경 구축
# 목차
1. [CDK 배포](#CDK-배포)
1. [쿠버네티스 대시보드 접속](#쿠버네티스-대시보드-접속)
1. [빌드 환경 수정](#빌드-환경-수정)
1. [파이프라인 설정](#파이프라인-설정)
   

-  [CDK 삭제](#CDK-삭제)
-  [CDK 스택 수정](#CDK-스택-수정)

## 요구사항  
- Cloud9 (IDE)
- Slack 채널의 Web Hook URL 
---
<br><br>

# CDK 배포
## 1. Cloud9에 접속
 ![Cloud9](https://user-images.githubusercontent.com/36617783/120590494-93833780-c475-11eb-950d-0ef021bf8e09.png)
<br><br>

## 2. AWS 임시 자격증명 해제
![image](https://user-images.githubusercontent.com/36617783/120590705-ec52d000-c475-11eb-84eb-c70ed0c53a2a.png)

설정 → AWS Settings → Credentials → AWS managed temporary credentials 체크 해제
<br><br>

## 3. AWS IAM 사용자 추가
```bash
aws configure
```
![image](https://user-images.githubusercontent.com/36617783/120591375-ff19d480-c476-11eb-9d49-e81634ee7be7.png)

AWS IAM → 사용자 → 보안 자격 증명탭을 확인하면 액세스 키를 발급 받을 수 있다.

### profile 설정
```bash
#aws configure --profile [name]
aws configure --profile noose
```
위 aws configure 설정값과 동일하게 입력한다.

<br><br>

## 4. 환경변수 세팅
```bash
sudo yum install -y jq
export ACCOUNT_ID=$(aws sts get-caller-identity --output text --query Account)
export AWS_REGION=$(curl -s 169.254.169.254/latest/dynamic/instance-identity/document | jq -r '.region')
echo "export ACCOUNT_ID=${ACCOUNT_ID}" | tee -a ~/.bash_profile
echo "export AWS_REGION=${AWS_REGION}" | tee -a ~/.bash_profile
aws configure get default.region # region 확인
```
<br><br>

## 5. kubectl 설치
```bash
curl -LO https://storage.googleapis.com/kubernetes-release/release/v1.17.0/bin/linux/amd64/kubectl
chmod +x ./kubectl
sudo mv ./kubectl /usr/local/bin/kubectl
kubectl help
```
<br><br>

## 6. CDK 환경을 위한 라이브러리 설치
```bash
sudo yum install -y npm
npm install -g aws-cdk@1.30.0 --force
npm install -g typescript@latest
```
<br><br>

## 7. CDK 빌드
```bash
git clone https://github.com/n00s3/aws_devsecops
cd aws_devsecops/cdk
cdk init
npm install
npm run build
cdk ls
```
<br><br>

## 8. CDK 배포
```bash
cdk synth --profile [name]
cdk bootstrap aws://$ACCOUNT_ID/$AWS_REGION --profile [name]
cdk deploy --profile [name]
```
![cdk deploy](https://user-images.githubusercontent.com/36617783/120595126-e2809b00-c47c-11eb-98c7-719a8c345f4e.png)

스택 생성을 하는데 클러스터 생성 과정이 포함되어 있어 **15~20분** 정도 소요된다.

|명령어|설명|
|------|---|
|cdk synth|AWS CDK 애플리케이션을 AWS CloudFormation 템플릿으로 컴파일합니다.  (cdk.out 디렉터리에 출력)|
|cdk bootstrap| AWS CDK 앱을 환경 (계정/리전)에 배포하기 위해서는 먼저 bootstrap stack이라는 것을 설치해야 한다.|
|cdk deploy| CDK 배포|
<br><br>


## 9. 스택 생성 확인
![cdk](https://user-images.githubusercontent.com/36617783/120597274-d0ecc280-c47f-11eb-8b3d-49e8fd81841e.png)

- CdkStackDevops : 배포된 스택
- CDKToolkit : 부트스트랩 스택
> AWS::EKS::Cluster는 Kubernetes 리소스에 대한 기본 제어 권한이 없다.  
> 그렇기 때문에 Lambda 함수나 IAM 역할 등이 포함된 중첩 스택이 별도로 설치된다.

<br><br>


## 10. kubeconfig 업데이트
Cloud9 환경의 쿠버네티스와 EKS와 매핑하는 작업이다.

Cloudformation → 스택 선택 → 출력  
**CdkStackDevops** 스택의 출력값을 확인하면 **ClusterConfigCommand**의 값을 복사 후 실행한다.
```bash
aws eks update-kubeconfig --name <Cluster_NAME> --region ap-northeast-2 --role-arn <ROLE_ARN>
```

### 노드 확인
```bash
kubectl get nodes
```
<br><br>


## 10. sh 스크립트를 사용해 컨테이너 배포와 인그레스 설치

### **Route53 도메인 또는 도메인이 있는 경우**
자신의 도메인에 맞게 yaml파일의 호스트를 수정한다.
```bash
cd ../docker-app/k8s/k8s_backup
vi devopsALBIngress_query1.yaml
```

```bash
cd ..
chmod +x setup2.sh
INSTANCE_ROLE=$(aws cloudformation describe-stack-resources --stack-name CdkStackDevOps | jq .StackResources[].PhysicalResourceId | grep CdkStackDevOps-ClusterDefaultCapacityInstanceRol | tr -d '["\r\n]')
CLUSTER_NAME=$(aws cloudformation describe-stack-resources --stack-name CdkStackDevOps | jq '.StackResources[] | select(.ResourceType=="Custom::AWSCDK-EKS-Cluster").PhysicalResourceId' | tr -d '["\r\n]')
echo "INSTANCE_ROLE = " $INSTANCE_ROLE 
echo "CLUSTER_NAME = " $CLUSTER_NAME
./setup2.sh $AWS_REGION $INSTANCE_ROLE $CLUSTER_NAME
```
setup2.sh 스크립트를 통해 Blue, Green, ARX_API서버, Sonarqube 컨테이너가 생성되고 로드밸런서가 생성된다.


### 로드밸런서 확인
![image](https://user-images.githubusercontent.com/36617783/120639445-4cfcff80-c4ac-11eb-9f85-8d9ccc04a10a.png)
![image](https://user-images.githubusercontent.com/36617783/120640092-0bb91f80-c4ad-11eb-8dab-768803ee4cd8.png)
호스트를 기반으로 라우팅한다.
<br><br>

### Route53 도메인 설정
![image](https://user-images.githubusercontent.com/36617783/120639887-d1e81900-c4ac-11eb-8f8f-4d2eed3d3e75.png)
1. ALB의 DNS 주소를 복사한다. 
2. Route53의 레코드를 CNAME 유형으로 리스너 규칙에 맞게 등록한다. 

<br><br>

### **Route53 도메인 또는 도메인이 없는 경우**
도메인이 없는 경우 쿼리 파라미터를 기반으로 라우팅 한다.
```bash
kubectl apply -f devopsALBIngress_query.yaml
```
<br><br>

## 11. 클러스터 보안 그룹 수정
![image](https://user-images.githubusercontent.com/36617783/120640552-9437c000-c4ad-11eb-9f51-8eef80161b5d.png)

ClusterDefaultCapacityInstanceSecurityGroup의 인바운드에 80포트(HTTP)를 열어준다.
<br><br>

## 12. 접속 확인
![image](https://user-images.githubusercontent.com/36617783/120640781-d5c86b00-c4ad-11eb-8d03-7941f308eeea.png)
![image](https://user-images.githubusercontent.com/36617783/120641025-1a540680-c4ae-11eb-854e-8a0ed991dce1.png)
![image](https://user-images.githubusercontent.com/36617783/120641088-2a6be600-c4ae-11eb-8e4a-267264978a11.png)
![image](https://user-images.githubusercontent.com/36617783/120641167-3f487980-c4ae-11eb-9d33-e8463a143c52.png)
 <br><br>

## 13. SecurityHub, Guardduty 활성화
SCA, SAST, DAST 보고서를 받을 수 있도록 대시보드에서 활성화 한다.
<br><br><br><br>

# 쿠버네티스 대시보드 접속
Cloud9 → Tools → Preview Running Application → 브라우저  
브라우저에 주소 입력  
**Cloud9_URL**/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/

```bash
# 토큰 확인
kubectl -n kubernetes-dashboard describe secret $(kubectl -n kubernetes-dashboard get secret | grep admin-user | awk '{print $1}')
```
<br><br><br><br>

# 빌드 환경 수정
## 1. 빌드 요구사항
빌드를 하기에 앞서 자신의 환경에 맞게 몇가지를 수정해야 한다.
<br><br>

## 2. Lambda 코드 수정
Cloudformation의 CdkStackDevOps 스택 출력값 확인
- S3Bucket
- lambdaSecurityHub
- lambdaSlack  

![image](https://user-images.githubusercontent.com/36617783/120732889-072e4e80-c521-11eb-898e-3b2bb53667ae.png)

lambdaSecurityHub, lambdaSlack 함수명을 확인하고 각 AWS Lambda에서 함수를 수정한다.
```python
### import_findings_security_hub.py
#s3bucket = "myfirstbucket" 
s3bucket = cdkstackdevops-myfirstbucketb8884501-1wki5u8hkln10 #S3Bucket 출력값으로 수정한다.
```

```python
### slack.py
#url = "https://hooks.slack.com/services/"
url = 'Slack 채널의 Web Hook URL'
```
<br><br>

## 3. CodeBuild SAST 프로젝트 환경변수 수정
Sonarqube 프로젝트에 맞게 환경변수 값을 세팅해야 한다.  
![image](https://user-images.githubusercontent.com/36617783/120734162-655c3100-c523-11eb-843c-0d189bbaf9df.png)

1. 자신의 sonarqube 주소로 접속
2. admin/admin 로그인
3. 'Create new project' 클릭
4. 'Project Key' 입력  
    환경변수 **SonarQube_Project**의 값과 같아야 한다.  
    만약 Sonarqube Project Key를 'test'로 만들었다면 SonarQube_Project 값도 'test'로 동일하게 변경한다.
5. token을 생성하고 제공되는 token값을 복사 한다.
6. 복사한 token 키값을 **SonarQube_Access_Token** 값에 입력한다.
7. **SonarQube_URL** 값은 자신의 sonarqube URL로 입력한다.
<br><br>

## 4. CodeBuild DAST 프로젝트 환경변수 수정
동적분석 수행 대상을 설정해야 한다.
1. AWS CodeBuild 접속
2. DAST 프로젝트 선택 후 편집 
3. 환경 클릭
4. hostname 값을 자신의 테스트 서버 URL로 수정한다.

<br><br><br><br>


# 파이프라인 설정
## CodeCommit 요구사항
![image](https://user-images.githubusercontent.com/36617783/120642376-c34f3100-c4af-11eb-9fd5-de241caabc56.png)
<br><br>

## CodeCommit 레포지토리에 Push
```bash
git remote add codecommit https://git-codecommit.$AWS_REGION.amazonaws.com/v1/repos/CdkStackDevOps-repo
git push codecommit master
```
> Push시 unable to access 에러가 발생하는 경우 아래와 같은 명령어를 입력한다.
```bash
git config --global --unset credential.helper
```
> CodeCommit Access key는 AWS IAM → 사용자 → 보안 자격 증명탭에서 발급 받을 수 있다.
<br><br>

### 트리거가 작동하며 파이프라인이 실행된다.
![image](https://user-images.githubusercontent.com/36617783/120642644-1f19ba00-c4b0-11eb-9bac-bacc88da5447.png)
<br><br><br><br>



# CDK 삭제
```bash
kubectl delete svc/devops-svc-alb-blue svc/devops-svc-alb-green svc/devops-svc-alb-api svc/devops-svc-alb-sonarqube -n devops-alb

kubectl delete deploy/devops-deploy-alb-blue deploy/devops-deploy-alb-api deploy/devops-deploy-alb-sonarqube deploy/devops-deploy-alb-green -n devops-alb

kubectl delete ingress alb-ingress -n devops-alb

kubectl delete deploy alb-ingress-controller -n kube-system

kubectl delete deployment,service kubernetes-dashboard -n kube-system

cdk destroy --profile [name]
```
<br><br><br><br>


# CDK 스택 수정
```bash
cd cdk/lib
vi cdk-stack.ts # stack 수정

# 재배포
cd ..
npm run build
cdk synth --profile [name]
cdk diff --profile [name]
cdk deploy --profile [name]
```
![image](https://user-images.githubusercontent.com/36617783/120732363-21b3f800-c520-11eb-9a80-1e818b712711.png)
cdk diff 명령어를 수행하면 삭제/추가 되는 리소스를 확인 가능하다.




1. 전체적인 인프라를 구성하는 스택을 변경하고 싶다면 **cdk-stack.ts**을 수정
2. 자신의 빌드 환경에 맞게 구성하고 싶으면 **buildspec.yaml** 파일을 수정
 