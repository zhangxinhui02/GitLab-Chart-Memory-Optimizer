import os
import sys
import yaml
import copy

# 优化参数
DISABLE_RESOURCES_REQUEST = True
DISABLE_HPA = True
PUMA_WORKER_PROCESSES = 0
SIDEKIQ_CONCURRENCY = 5

# 补丁输出文件夹
OUTPUT_DIR = './output/'

if not os.path.exists(OUTPUT_DIR) or not os.path.isdir(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# 读取源清单文件
kube_objects = []
for root, dirs, files in os.walk(sys.argv[1], followlinks=True):
    for file in files:
        if file.endswith(".yaml"):
            with open(os.path.join(root, file), "r", encoding='utf-8') as f:
                rows = f.readlines()
            _tmp_yaml = ''
            for row in rows:
                if not row.startswith('---'):
                    _tmp_yaml += row
                else:
                    kube_objects.append(yaml.safe_load(_tmp_yaml))
                    _tmp_yaml = ''
            if _tmp_yaml.strip() != '':
                kube_objects.append(yaml.safe_load(_tmp_yaml))
for kube_object in kube_objects:
    if kube_object is None:
        kube_objects.remove(kube_object)

objects_to_delete = []
objects_to_create = []

# 遍历清单文件
for kube_object in kube_objects:
    is_delete = False
    is_create = False
    original_object = copy.deepcopy(kube_object)

    # 移除HPA
    if DISABLE_HPA:
        if kube_object['kind'] == 'HorizontalPodAutoscaler':
            is_delete = True
        if kube_object['kind'] == 'Deployment':
            is_delete = True
            kube_object['spec']['replicas'] = 1
            is_create = True

    # 移除资源申请
    if DISABLE_RESOURCES_REQUEST:
        if kube_object['kind'] == 'Pod':
            containers = kube_object['spec']['containers']
        elif kube_object['kind'] in ['Deployment', 'StatefulSet']:
            containers = kube_object['spec']['template']['spec']['containers']
        else:
            containers = []
        for container in containers:
            if 'resources' in container:
                is_delete = True
                del container['resources']
                is_create = True

    # 设置Puma worker_process
    if PUMA_WORKER_PROCESSES is not None:
        if kube_object['kind'] == 'Deployment' and kube_object['metadata']['labels']['app'] == 'webservice':
            for container in kube_object['spec']['template']['spec']['containers']:
                if container['name'] == 'webservice':
                    for env in container['env']:
                        if env['name'] == 'WORKER_PROCESSES':
                            is_delete = True
                            env['value'] = str(PUMA_WORKER_PROCESSES)
                            is_create = True

    # 设置Sidekiq concurrency
    if SIDEKIQ_CONCURRENCY is not None:
        if kube_object['kind'] == 'Deployment' and kube_object['metadata']['labels']['app'] == 'sidekiq':
            for container in kube_object['spec']['template']['spec']['containers']:
                if container['name'] == 'sidekiq':
                    for env in container['env']:
                        if env['name'] == 'SIDEKIQ_CONCURRENCY':
                            is_delete = True
                            env['value'] = str(SIDEKIQ_CONCURRENCY)
                            is_create = True

    if is_delete:
        objects_to_delete.append(original_object)
    if is_create:
        objects_to_create.append(kube_object)

# 输出补丁文件
with open(os.path.join(OUTPUT_DIR, 'delete.yaml'), 'w', encoding='utf-8') as f:
    for kube_object in objects_to_delete:
        f.write(yaml.safe_dump(kube_object))
        f.write('---\n')
with open(os.path.join(OUTPUT_DIR, 'create.yaml'), 'w', encoding='utf-8') as f:
    for kube_object in objects_to_create:
        f.write(yaml.safe_dump(kube_object))
        f.write('---\n')
with open(os.path.join(OUTPUT_DIR, 'run.sh'), 'w', encoding='utf-8') as f:
    delete_cmd = ''
    for kube_object in objects_to_delete:
        delete_cmd += (f'kubectl delete '
                       f'-n {kube_object["metadata"]["namespace"]} '
                       f'{kube_object["kind"]} '
                       f'{kube_object["metadata"]["name"]}\n')
    run_sh = f"""#!/bin/sh
set -x
# kubectl delete -f delete.yaml
{delete_cmd}
sleep 5
kubectl apply -f create.yaml
echo 'Gitlab was optimized successfully.'
"""
    f.write(run_sh)

os.system(f'chmod +x {os.path.join(OUTPUT_DIR, "run.sh")}')
print(f'Gitlab patch files were generated in `{OUTPUT_DIR}` dir. Execute `run.sh` to patch GitLab.')
