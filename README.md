# GitLab Chart Memory Optimizer

GitLab功能强大，本身会占用很多内存资源。通过Helm Chart部署GitLab到k8s时，为了保证高可用，默认会部署更多的冗余资源，导致更多的内存占用。

如果你的k8s集群并没有那么多内存，你也不在乎高可用，那么你可以使用这个脚本来禁用GitLab在k8s内的一些冗余部署和功能，降低内存占用。

## 适用版本

仅在`https://charts.gitlab.io`官方仓库的`8.11.4`版本的gitlab chart中测试过，对应GitLab版本为`v17.11.4`。其他版本无法保证可用性。

## 使用方法

1. 在安装/升级GitLab实例前，渲染出即将安装的所有清单文件到任意目录。

   ```sh
   helm template mygitlab gitlab/gitlab -n mygitlab --values mygitlab.yaml --output-dir ./input
   ```

2. 运行优化脚本，传入清单文件目录作为参数，生成优化补丁。

   ```sh
   python optimizer.py ./input
   ```
   
   补丁文件会生成在`./output`目录中。

3. 正常安装GitLab实例。

   ```sh
   helm upgrade --install mygitlab gitlab/gitlab -n mygitlab --values mygitlab.yaml
   ```
   
   等待helm命令正常执行完毕。

4. 应用优化补丁。

   ```sh
   cd ./output
   ./run.sh
   ```
   
   等待服务启动即可。

## 注意事项

每次进行helm安装/升级/回滚，都会导致优化项被还原。因此每次进行这些操作后，都需要同步应用补丁。
