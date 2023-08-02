from robusta.api import *
from kubernetes import client as kubeclient, config
from datetime import datetime, timedelta
from client.victoriametrics import VictoriaMetrics, Deployment

import logging
import time

CPU_UTIL_THRESHOLD = 90
MEMORY_UTIL_THRESHOLD = 90

def get_max(util_per_container):
    max_utils = []
    for util in util_per_container:
        tmp = list(map(lambda x: float(x[1]), util['values']))
        max_utils.append(max(tmp))
    return max(max_utils)


def is_oomkilled(namespace, deployment_name):
    v1 = kubeclient.CoreV1Api()
    ret = v1.list_namespaced_pod(namespace=namespace)
    for i in ret.items:
        if i.metadata.labels.get('app') == deployment_name:
            for j in i.status.container_statuses:
                if j.last_state.terminated and j.last_state.terminated.reason == 'OOMKilled':
                    logging.info(f'deployment {deployment_name} OOMKilled')
                    return True

    return False

def need_more_resource(namespace, deployment_name):
    # nice to have: check log for obvious crashing reason thus not having to check resource
    end_time = int(time.time())
    start_time = end_time - (1 * 30 * 60) # 30 minutes # TODO: Don't hardcode duration
    client = VictoriaMetrics(start_time, end_time)
    depl = Deployment(VictoriaMetrics.cluster_staging, namespace, deployment_name) # TODO: Don't hardcode cluster

    mem_util = client.get_deployment_memory_utilization_per_container(depl)
    cpu_util = client.get_deployment_cpu_utilization_per_container(depl)

    max_cpu_util = get_max(cpu_util)
    max_memory_util = get_max(mem_util)

    if max_cpu_util > CPU_UTIL_THRESHOLD or max_memory_util > MEMORY_UTIL_THRESHOLD:
        return True

    return False

@action
def determine_cause(alert: PrometheusKubernetesAlert):
    # big question, what if dev has already manually scale up the resource?
    # and we need to have some sort of limitation on how many times should we trigger this
    try:
        config.load_kube_config()
    except:
        config.load_incluster_config()

    try:
        alert_subject = alert.get_alert_subject()
        subject_type = alert_subject.subject_type.value
        resource_name = alert_subject.name
        namespace = alert_subject.namespace
        if subject_type != "deployment":
            logging.info(f"skipping {resource_name} because its type is {subject_type}")

        if is_oomkilled(namespace, resource_name):
            logging.info(f"{resource_name} is oomkilled, should increase memory")
            return

        if need_more_resource(namespace, resource_name):
            logging.info(f"{resource_name} is crashing cause of the lack of resource")
            return

        logging.info(f"cannot automatically repair {resource_name}")
        return
    except Exception as e: print(e)

