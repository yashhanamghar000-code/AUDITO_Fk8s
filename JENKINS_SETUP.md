# Jenkins deployment setup

This pipeline builds and pushes the Anthropic Claude LLM service, deploys it to
Kubernetes, and configures the ingress for `auditoai.online`.

## 1. Jenkins agent requirements

Install Docker, `kubectl`, Git, and the Jenkins Credentials Binding plugin on
the agent. The agent user must be allowed to run Docker.

## 2. Add Jenkins credentials

In **Manage Jenkins > Credentials > System > Global credentials**, add:

| ID | Kind | Value |
|---|---|---|
| `dockerhub-credentials` | Username with password | Docker Hub username and access token |
| `kubeconfig` | Secret file | Kubeconfig for the target cluster |
| `anthropic-api-key` | Secret text | Anthropic API key |
| `audito-tls-crt` | Secret file | TLS certificate for `auditoai.online` |
| `audito-tls-key` | Secret file | Matching TLS private key |

Do not store any of these values in Git or as plain Jenkins parameters.

## 3. Prepare Kubernetes

Install an NGINX ingress controller in the cluster. The rest of the application
manifests and their required secrets must already be deployed; this pipeline
updates the LLM service and public ingress only.

Check the ingress controller's public address:

```bash
kubectl get ingressclass
kubectl -n ingress-nginx get service ingress-nginx-controller
```

At the DNS provider for `auditoai.online`, create an `A` record pointing to the
ingress controller's external IP. If the provider returns a hostname instead,
create the appropriate `CNAME` record.

## 4. Create the Jenkins job

1. Push `Jenkinsfile` and the related source/manifests to the Git repository.
2. In Jenkins, select **New Item > Pipeline**.
3. Under **Pipeline**, choose **Pipeline script from SCM** and select Git.
4. Enter the repository URL and credentials, use branch `*/main`, and keep the
   script path as `Jenkinsfile`.
5. Run **Build Now**.

## 5. Verify

```bash
kubectl -n audito get pods
kubectl -n audito get ingress
kubectl -n audito logs deployment/llm-service --tail=100
curl -I https://auditoai.online
```

The LLM pod should show `Running` and `READY 1/1`. DNS changes can take time to
propagate depending on the DNS provider's TTL.
