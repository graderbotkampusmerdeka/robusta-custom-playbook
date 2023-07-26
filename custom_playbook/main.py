from client.victoriametrics import VictoriaMetrics, Deployment
import time

if __name__ == "__main__":
    end_time = int(time.time())
    start_time = end_time - (1 * 60 * 60) # 1 hour
    client = VictoriaMetrics(start_time, end_time)
    depl = Deployment(VictoriaMetrics.cluster_staging, "robusta", "logerrorapp")

    print(client.get_deployment_memory_utilization_per_container(depl))
