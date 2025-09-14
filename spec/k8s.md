% Kubernetes 部署指南

## 概览
本指南提供最小可用的 K8s 部署清单：命名空间、ConfigMap、Secret、Deployment、Service 与 Ingress。建议在生产中使用 Ingress/网关终止 TLS，并通过 Secret/ConfigMap 注入配置与密钥。

## 前置准备
- 已构建并推送镜像（示例：`your-registry/ai-api-example:0.1.0`）。
- 集群中可用的 Ingress Controller（如 NGINX Ingress）。
- 可选：cert-manager 用于自动签发 TLS 证书。

## 命名空间
```bash
kubectl create namespace ai
```

## Secret（敏感配置）
使用命令创建，避免将密钥写入仓库：
```bash
kubectl -n ai create secret generic ai-api-secrets \
  --from-literal=DASHSCOPE_API_KEY=sk-... \
  --from-literal=INTERNAL_API_KEY=$(openssl rand -hex 32)
```

## ConfigMap（非敏感配置）
根据需要修改 `k8s/configmap.yaml`，然后：
```bash
kubectl -n ai apply -f k8s/configmap.yaml
```

## 部署与服务
将 `k8s/deployment.yaml` 中的镜像替换为你推送的镜像，然后：
```bash
kubectl -n ai apply -f k8s/deployment.yaml
kubectl -n ai apply -f k8s/service.yaml
```

## Ingress（可选，TLS 建议在此终止）
编辑 `k8s/ingress.yaml` 将域名替换为你的域名，准备 TLS Secret：
- 手动方式：`kubectl -n ai create secret tls ai-api-tls --key key.pem --cert cert.pem`
- 或使用 cert-manager（推荐）：配置 ClusterIssuer 后由 Ingress 注解自动签发。

应用 Ingress：
```bash
kubectl -n ai apply -f k8s/ingress.yaml
```

## 验证
```bash
kubectl -n ai get pods -l app=ai-api
kubectl -n ai logs deploy/ai-api
curl -k https://api.example.com/health
```

## 进阶建议
- 水平扩展与弹性：为 Deployment 启用 HPA，依据 CPU/QPS 伸缩。
- 资源与限流：根据负载调整 requests/limits 与应用内限流参数。
- 统一日志与追踪：接入 ELK/OTEL，启用结构化日志与分布式追踪。
- 安全：NetworkPolicy 限制东西向访问；将 `GET /chat/stream` 暴露限制在受控前端域名。

