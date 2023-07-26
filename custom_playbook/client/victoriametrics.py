
class Deployment:
    def __init__(self, cluster_name, namespace, name):
        self.cluster_name = cluster_name
        self.namespace = namespace
        self.name = name

class VictoriaMetrics:
    cluster_infra = 'ase1-glo-infra-1'
    cluster_prod_id = 'ase1-id-prod-1'
    cluster_prod_th = 'ase1-th-prod-1'
    cluster_prod_vn = 'ase1-vn-prod-1'
    cluster_staging = 'ruangguru-k8s'

    namespace_to_cluster_map = {
        "robusta": cluster_staging,
        "staging": cluster_staging,
        "th-staging": cluster_staging,
        "vn-staging": cluster_staging,
        "production": cluster_prod_id,
        "th-production": cluster_prod_th,
        "vn-production": cluster_prod_vn,
    }

    clusters_victoria_map = {
        cluster_infra: 0,
        cluster_staging: 1,
        cluster_prod_id: 4,
        cluster_prod_th: 5,
        cluster_prod_vn: 6,
    }

    endpoints = {
        "query_range": "query_range"
    }

    step_multiplier = 10
    rate_multiplier = 15
    seconds_in_hour = 60*60

    sidecar_container_regex = 'istio-proxy|linkerd-proxy'

    def __init__(self, start_time, end_time):
        self.base_url = 'http://vmselect.rg.internal:8481'
        self.start_time = start_time
        self.end_time = end_time

    def get_deployment_cpu_utilization_per_container(self, deployment):
        rate = self.get_rate(self.end_time - self.start_time)
        query = f"""
            WITH (
            commonFilters = {{k8s_cluster="{deployment.cluster_name}", namespace="{deployment.namespace}"}},
            podFilters = {{commonFilters, pod=~"{deployment.name}.*"}},
              namespace_deployment_pod = max(
                ceil(
                  label_replace(
                    kube_pod_owner{{commonFilters, owner_kind="ReplicaSet", owner_name=~"{deployment.name}.*"}}, "replicaset", "$1", "owner_name", "(.*)"
                  )
                  /
                  on(replicaset, namespace) group_left(deployment)
                  (max(kube_replicaset_spec_replicas{{commonFilters, replicaset=~"{deployment.name}.*"}}) by(namespace, replicaset) > 0)
                  *
                  on(replicaset, namespace) group_left(deployment)
                  max(label_replace(
                    kube_replicaset_owner{{commonFilters, owner_kind="Deployment", owner_name="{deployment.name}"}}, "deployment", "$1", "owner_name", "(.*)"
                  )) by(namespace, deployment, replicaset)
                )
              ) by(namespace, deployment, pod),
              namespace_deployment_container:avg_cpu_usage = avg(
                namespace_deployment_pod
                *
                on(namespace, pod) group_right(deployment)
                max(rate(
                  container_cpu_usage_seconds_total{{podFilters, container!="POD"}}[{rate}]
                )) by(namespace, pod, container)
              ) by(namespace, deployment, container),
              namespace_deployment_container:cpu_requests = max(
                namespace_deployment_pod
                *
                on(namespace, pod) group_right(deployment)
                max(kube_pod_container_resource_requests_cpu_cores{{podFilters}}) by(namespace, pod, container)
              ) by(namespace, deployment, container)
            )

            (namespace_deployment_container:avg_cpu_usage / namespace_deployment_container:cpu_requests) * 100
        """

        params = {
            "query": query,
            "start": self.start_time,
            "end": self.end_time,
            "step": self.get_step(self.end_time - self.start_time),
        }
        
        try:
            return self.__call__(endpoint=self.endpoints['query_range'], cluster=deployment.cluster_name, query_params=params)
        except Exception as e: 
            raise e
    
    def get_deployment_memory_utilization_per_container(self, deployment):
        query = f"""
            WITH (
            commonFilters = {{k8s_cluster="{deployment.cluster_name}", namespace="{deployment.namespace}"}},
            podFilters = {{commonFilters, pod=~"{deployment.name}.*"}},
              namespace_deployment_pod = max(
                ceil(
                  label_replace(
                    kube_pod_owner{{commonFilters, owner_kind="ReplicaSet", owner_name=~"{deployment.name}.*"}}, "replicaset", "$1", "owner_name", "(.*)"
                  )
                  /
                  on(replicaset, namespace) group_left(deployment)
                  (max(kube_replicaset_spec_replicas{{commonFilters, replicaset=~"{deployment.name}.*"}}) by(namespace, replicaset) > 0)
                  *
                  on(replicaset, namespace) group_left(deployment)
                  max(label_replace(
                    kube_replicaset_owner{{commonFilters, owner_kind="Deployment", owner_name="{deployment.name}"}}, "deployment", "$1", "owner_name", "(.*)"
                  )) by(namespace, deployment, replicaset)
                )
              ) by(namespace, deployment, pod),
              namespace_deployment_container:avg_memory_usage = avg(
                namespace_deployment_pod
                *
                on(namespace, pod) group_right(deployment)
                max(
                  container_memory_working_set_bytes{{podFilters, container!="POD"}}
                ) by(namespace, pod, container)
              ) by(namespace, deployment, container),
              namespace_deployment_container:memory_requests = max(
                namespace_deployment_pod
                *
                on(namespace, pod) group_right(deployment)
                max(kube_pod_container_resource_requests_memory_bytes{{podFilters}}) by(namespace, pod, container)
              ) by(namespace, deployment, container)
            )

            (namespace_deployment_container:avg_memory_usage / namespace_deployment_container:memory_requests) * 100
        """

        params = {
            "query": query,
            "start": self.start_time,
            "end": self.end_time,
            "step": self.get_step(self.end_time - self.start_time),
        }
        
        try:
            return self.__call__(endpoint=self.endpoints['query_range'], cluster=deployment.cluster_name, query_params=params)
        except Exception as e: 
            raise e
    
    def __call__(self, endpoint, cluster, query_params):
        if cluster not in self.clusters_victoria_map:
            raise Exception(f"cluster {self.clusters_victoria_map} not found")
        
        import requests
        from requests.adapters import HTTPAdapter, Retry

        headers = {
            "Accept": "application/json"
        }
        
        s = requests.Session()
        retries = Retry(total=5,
                backoff_factor=0.1,
                status_forcelist=[ 500, 502, 503, 504 ])
        s.mount('http://', HTTPAdapter(max_retries=retries))
        r = s.get(f'{self.base_url}/select/{self.clusters_victoria_map[cluster]}/prometheus/api/v1/{endpoint}', params=query_params, headers=headers)
        if r.ok:
            return r.json()['data']['result']
        
        raise Exception(f"request failed with {r.json()}")
    
    def get_step(self, duration_in_seconds):
        return int(duration_in_seconds * self.step_multiplier / self.seconds_in_hour)

    def get_rate(self, duration_in_seconds):
        rate = int(duration_in_seconds * self.rate_multiplier / self.seconds_in_hour)
        return f'{rate}s'
