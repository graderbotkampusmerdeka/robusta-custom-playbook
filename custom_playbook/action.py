from robusta.api import *
import logging

from kubernetes import client, config
from kubernetes.client import V1Job
from kubernetes.client.models.v1_job_spec import V1JobSpec
from kubernetes.client.models.v1_pod_template_spec import V1PodTemplateSpec
from kubernetes.client.models.v1_pod_spec import V1PodSpec
from kubernetes.client.models.v1_container import V1Container
from kubernetes.client.models.v1_object_meta import V1ObjectMeta
import uuid

def create_job_object(deployment_name, percentage):
    job_name = "robusta-job-" + str(uuid.uuid4())
    # Configureate Pod template container
    container = V1Container(
        name=job_name,
        image="asia-southeast1-docker.pkg.dev/silicon-airlock-153323/infrastructure/robusta-job-runner:ee13c22e68",
        command=["/root/increase-memory.sh", "robusta", deployment_name, percentage])

    # Create and configurate a spec section
    template = V1PodTemplateSpec(
        metadata=V1ObjectMeta(labels={"app": job_name}),
        spec=V1PodSpec(containers=[container], restart_policy="Never", service_account_name="robusta-jenkins-sa"))

    # Create the specification of deployment
    spec = V1JobSpec(
        template=template,
        backoff_limit=4)

    # Instantiate the job object
    job = V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=V1ObjectMeta(name=job_name),
        spec=spec)

    return job

def create_job(api_instance, job):
    api_response = api_instance.create_namespaced_job(
        namespace="robusta",
        body=job)
    print("Job created. status='%s'" % str(api_response.status))

@action
def custom_action(alert: PrometheusKubernetesAlert):
    try:
        config.load_kube_config()
    except:
        config.load_incluster_config()


    try:
        alert_subject = alert.get_alert_subject()
        logging.info(f"[custom_action] upscaling {alert_subject.subject_type.value} - {alert_subject.name}")

        batch_v1 = client.BatchV1Api()
        job = create_job_object(alert_subject.name, 100)
        create_job(batch_v1, job)
    except Exception as e: print(e)
