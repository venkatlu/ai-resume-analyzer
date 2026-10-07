"""Skill taxonomy: canonical name | alias | alias ...  (all lowercase)."""

_RAW = """
python|python3
java
javascript|js|ecmascript
typescript
c++|cpp
c#|csharp
c programming
php
golang
rust
kotlin
swift
ruby
scala
matlab
r programming
sql
mysql
postgresql|postgres
mongodb|mongo
sqlite
oracle
redis
firebase
nosql
html|html5
css|css3
sass|scss
tailwind css|tailwind
bootstrap
react|react.js|reactjs
angular|angularjs
vue|vue.js|vuejs
next.js|nextjs
node.js|nodejs|node
express|express.js|expressjs
django
flask
fastapi
spring boot|springboot
spring
laravel
asp.net
rest api|rest apis|restful|restful api|restful apis|rest
graphql
websockets|websocket
microservices
json
xml
ajax
jquery
mern|mern stack
full stack|full-stack|fullstack
git
github
gitlab
bitbucket
docker
kubernetes|k8s
jenkins
ci/cd|cicd|ci cd
github actions
terraform
ansible
linux
bash|shell scripting
aws|amazon web services
azure
gcp|google cloud
oracle cloud|oci
heroku
netlify|vercel
nginx
apache
postman
swagger|openapi
jira
agile
scrum
machine learning|ml
deep learning
artificial intelligence|ai
natural language processing|nlp
computer vision
generative ai|gen ai
large language models|llm|llms
langchain
prompt engineering
tensorflow
keras
pytorch
scikit-learn|sklearn
opencv
yolo|yolov8
hugging face|huggingface
transformers
spacy
nltk
pandas
numpy
matplotlib
seaborn
scipy
data analysis
data visualization
data structures
algorithms
data science
data engineering
big data
hadoop
spark|pyspark
kafka
airflow
etl
power bi|powerbi
tableau
excel|microsoft excel
statistics
oop|object oriented programming|object-oriented programming|object oriented
design patterns
system design
unit testing
junit
pytest
selenium
jest
test driven development|tdd
debugging
cybersecurity|cyber security
network security
penetration testing
owasp
encryption
authentication
jwt
oauth
iot|internet of things
embedded systems
arduino
raspberry pi
android
ios
flutter
react native
responsive design
ui/ux|ux|ui design
figma
problem solving
communication
teamwork|collaboration
leadership
time management
critical thinking
"""

SKILL_ALIASES = {}
for _line in _RAW.strip().splitlines():
    _parts = [p.strip() for p in _line.split("|") if p.strip()]
    SKILL_ALIASES[_parts[0]] = _parts

SOFT_SKILLS = {"problem solving", "communication", "teamwork", "leadership",
               "time management", "critical thinking"}
