# 工作命令手册（整理版）

> 基于桌面原始 `handbook.md` 重整。
> 目标：更便于检索、复制和按场景使用。
> 说明：原文中的敏感信息（API Key、Token）已不在本文件中展开，建议改存到密码管理器或 `.env`。

## 目录

1. [通用 Linux 命令](#通用-linux-命令)
2. [vLLM / llama.cpp 快速索引](#vllm--llamacpp-快速索引)
3. [10.10.11.21](#10101121)
4. [10.10.11.22](#10101122)
5. [10.10.11.31](#10101131)
6. [媒体下载与转码](#媒体下载与转码)
7. [WAN / 视频生成](#wan--视频生成)
8. [Ollama](#ollama)
9. [代理 / SSH 反向隧道](#代理--ssh-反向隧道)
10. [Docker](#docker)
11. [Hugging Face / 其他工具](#hugging-face--其他工具)
12. [Nginx](#nginx)
13. [敏感信息存放建议](#敏感信息存放建议)

---

## 通用 Linux 命令

### 路径与文件

```bash
pwd
cd <dir>
df -h
du -h --max-depth=1 | sort -hr
zip -r dialog.zip role_dialog/
rm -rf <path>
trash-empty
```

### 权限

```bash
sudo chown -R shenyh officialWeights
sudo su
```

### GPU / 进程

```bash
watch -n 1 nvidia-smi
ps -u $USER -o pid,tty,cmd | grep -E 'bash|sh|zsh'
```

### tmux

```bash
sudo apt install tmux
tmux
tmux ls
tmux attach -t <session_name>
exit
```

### uv / Python 虚拟环境

```bash
source .venv/bin/activate
```

### 临时清空环境变量

```bash
export LD_LIBRARY_PATH=""
export PYTHONPATH=""
```

### 挂载磁盘

```bash
lsblk
lsblk -f
sudo mount UUID=301160e1-ee06-490d-b51f-c6130618f7e0 /data1
sudo mount UUID=4351804a-779d-4771-bf05-1a4cc775a8af /data2
```

### 驱动

```bash
sudo apt install nvidia-driver-575
```

### 文件传输

```bash
scp /mnt/tmp/shenyh/docker_mount/Qwen3.5-122B-Uncensored/Qwen3.5-122B-A10B-Uncensored-HauhauCS-Aggressive-Q8_K_P.gguf \
  tangpp1@10.10.11.22:/sdd2/official_weights/Qwen3.5-122B-A10B-Uncensored-HauhauCS-Aggressive-Q8_K_P/
```

---

## vLLM / llama.cpp 快速索引

### 通用 vLLM 启动示例

```bash
cd /sdd2/offical_weights
vllm serve "qwen3-32B" --port 8000 --enable-reasoning --reasoning-parser deepseek_r1
vllm serve "qwen3-32B" --port 8080 --enable-reasoning --reasoning-parser deepseek_r1
VLLM_USE_MODELSCOPE=true vllm serve "qwen3-32B" --port 8080 --tensor-parallel-size 4
```

### Qwen3-VL-32B

```bash
cd /home/tangpp1/.cache/modelscope/hub/models

VLLM_USE_MODELSCOPE=true \
vllm serve Qwen/Qwen3-VL-32B-Instruct \
  --tensor-parallel-size 4 \
  --port 8080 \
  --max-model-len 8192
```

---

## 10.10.11.21

### uv 环境

```bash
cd /home/chenyj/uv_env/gemma4
source .venv/bin/activate
```

### Qwen3.5-27B

```bash
LD_LIBRARY_PATH="" \
CUDA_VISIBLE_DEVICES=1,2,3,4 \
VLLM_USE_MODELSCOPE=true \
vllm serve Qwen3.5-27B \
  --port 8000 \
  --tensor-parallel-size 4 \
  --max-model-len 128000 \
  --reasoning-parser qwen3 \
  --max-num-seqs 8 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder
```

### Qwen3.5-35B-A3B

```bash
LD_LIBRARY_PATH="" \
VLLM_USE_MODELSCOPE=true \
vllm serve /data1/official_weights/Qwen3.5-35B-A3B \
  --tensor-parallel-size 4 \
  --port 8080 \
  --served-model-name Qwen3.5-35B-A3B
```

### Qwen3-Coder-Next-FP8

```bash
VLLM_USE_MODELSCOPE=true \
vllm serve /data1/official_weights/Qwen3-Coder-Next-FP8 \
  --port 8000 \
  --tensor-parallel-size 4 \
  --max-num-seqs 32 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --served-model-name Qwen3-Coder-Next-FP8
```

可选 parser 记录：

```bash
--tool-call-parser qwen3_coder
--tool-call-parser qwen3_xml
```

### GLM-4.7-Flash

```bash
VLLM_USE_MODELSCOPE=true \
vllm serve /data1/official_weights/GLM-4.7-Flash \
  --port 8000 \
  --tensor-parallel-size 4 \
  --speculative-config.method mtp \
  --speculative-config.num_speculative_tokens 1 \
  --tool-call-parser hermes \
  --reasoning-parser glm45 \
  --enable-auto-tool-choice \
  --served-model-name glm-4.7-flash
```

额外记录：

```bash
--tool-call-parser glm47
```

### Qwen3.5-122B-A10B-FP8

```bash
LD_LIBRARY_PATH="" \
VLLM_USE_MODELSCOPE=true \
vllm serve /data1/official_weights/Qwen3.5-122B-A10B-FP8 \
  --gpu-memory-utilization 0.85 \
  --max-num-seqs 256 \
  --tensor-parallel-size 4 \
  --port 8080 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --served-model-name Qwen3.5-122B-A10B-FP8
```

### gemma-4-31B-it

```bash
LD_LIBRARY_PATH="" \
CUDA_VISIBLE_DEVICES=4,5 \
vllm serve /data1/official_weights/gemma-4-31B-it \
  --served-model-name gemma-4-31B-it \
  --tensor-parallel-size 2 \
  --max-model-len 14000 \
  --gpu-memory-utilization 0.90 \
  --enable-auto-tool-choice \
  --reasoning-parser gemma4 \
  --tool-call-parser gemma4 \
  --limit-mm-per-prompt '{"image":4,"audio":1}' \
  --async-scheduling \
  --host 0.0.0.0 \
  --port 8000
```

### Qwen3-ASR-1.7B

```bash
LD_LIBRARY_PATH="" \
CUDA_VISIBLE_DEVICES=4 \
qwen-asr-serve /data1/official_weights/Qwen3-ASR-1.7B \
  --gpu-memory-utilization 0.8 \
  --host 0.0.0.0 \
  --port 8000 \
  --served-model-name Qwen3-ASR-1.7B
```

---

## 10.10.11.31

### 目录与基础模型

```bash
cd /mnt/tmp/shenyh/officialWeights
```

### Qwen3-14B

```bash
VLLM_USE_MODELSCOPE=true \
vllm serve "Qwen3-14B" \
  --port 8080 \
  --tensor-parallel-size 2 \
  --max-num-seqs 8
```

### MiMo-V2.5-ASR

```bash
python run_mimo_asr.py \
  --model-path /mnt/tmp/shenyh/officialWeights/MiMo-V2.5-ASR \
  --tokenizer-path /mnt/tmp/shenyh/officialWeights/MiMo-Audio-Tokenizer
```

### Docker 启动 Hermes

```bash
docker run -it \
  --name my_hermes_v2 \
  --network host \
  -v /mnt/tmp/shenyh/docker_mount \
  hermes-ready:v1 \
  /bin/bash
```

### llama.cpp

```bash
CUDA_VISIBLE_DEVICES=0,1 \
/home/shenyh/Py_project/llama.cpp-master/build/bin/llama-server \
  -m /mnt/tmp/shenyh/docker_mount/Qwen3.6-40B-Deck-Opus-NEO-CODE-HERE-Q8/Qwen3.6-40B-Deck-Opus-NEO-CODE-HERE-2T-OT-HIGH-Q8_0.gguf \
  --host 0.0.0.0 \
  --port 5000 \
  --jinja \
  -fa on \
  -b 2048 \
  -c 256000 \
  -ngl 99 \
  --reasoning-format none \
  -ub 2048
```

---

## 10.10.11.22

### Qwen3-VL-30B-A3B-Instruct

```bash
LD_LIBRARY_PATH="" \
CUDA_VISIBLE_DEVICES=0,1,2,3 \
vllm serve /sdd2/official_weights/Qwen3-VL-30B-A3B-Instruct \
  --tensor-parallel-size 4 \
  --port 8080 \
  --max-model-len 262144 \
  --served-model-name Qwen3-VL-30B-A3B-Instruct
```

### Qwen3.5-122B-A10B-FP8

```bash
LD_LIBRARY_PATH="" \
VLLM_USE_MODELSCOPE=true \
vllm serve /sdd2/official_weights/Qwen3.5-122B-A10B-FP8 \
  --gpu-memory-utilization 0.85 \
  --max-num-seqs 256 \
  --tensor-parallel-size 4 \
  --port 8080 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --served-model-name Qwen3.5-122B-A10B-FP8
```

### Qwen3.5-397B-A17B-GPTQ-Int4

```bash
LD_LIBRARY_PATH="" \
VLLM_USE_MODELSCOPE=true \
vllm serve /sdd2/official_weights/Qwen3.5-397B-A17B-GPTQ-Int4 \
  --gpu-memory-utilization 0.85 \
  --tensor-parallel-size 8 \
  --max-num-seqs 32 \
  --port 8080 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --reasoning-parser qwen3 \
  --served-model-name Qwen3.5-397B-A17B-GPTQ-Int4
```

### S2-PRO 语音模型

```bash
export LIBRARY_PATH=/usr/local/cuda/lib64/stubs:$LIBRARY_PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
```

```bash
python tools/api_server.py \
  --listen 0.0.0.0:8888 \
  --llama-checkpoint-path /data1/official_weights/s2-pro \
  --decoder-checkpoint-path /data1/official_weights/s2-pro/codec.pth \
  --compile
```

```bash
python fish_speech/models/dac/inference.py \
  -i "test.wav" \
  --checkpoint-path "/data1/official_weights/s2-pro/codec.pth"
```

### NVIDIA Nemotron-3-Super-120B-A12B-FP8

```bash
CUDA_VISIBLE_DEVICES=1,2,3,4 \
VLLM_USE_MODELSCOPE=true \
vllm serve /sdd2/official_weights/NVIDIA-Nemotron-3-Super-120B-A12B-FP8 \
  --served-model-name nemotron-3-super \
  --async-scheduling \
  --dtype auto \
  --kv-cache-dtype fp8 \
  --tensor-parallel-size 4 \
  --pipeline-parallel-size 1 \
  --data-parallel-size 1 \
  --swap-space 0 \
  --trust-remote-code \
  --attention-backend TRITON_ATTN \
  --gpu-memory-utilization 0.9 \
  --enable-chunked-prefill \
  --max-num-seqs 16 \
  --port 5000 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --reasoning-parser-plugin "/sdd2/official_weights/NVIDIA-Nemotron-3-Super-120B-A12B-FP8/super_v3_reasoning_parser.py" \
  --reasoning-parser super_v3
```

### Qwen3-ASR-1.7B

```bash
CUDA_VISIBLE_DEVICES=4 \
qwen-asr-serve /sdd2/official_weights/Qwen3-ASR-1.7B \
  --gpu-memory-utilization 0.8 \
  --host 0.0.0.0 \
  --port 8070 \
  --served-model-name Qwen3-ASR-1.7B
```

### GLM-5.1

llama.cpp 工作目录：

```bash
cd /home/tangpp1/llama.cpp-master
```

vLLM 环境：

```bash
source /home/tangpp1/uv_env/glm5.1/.venv/bin/activate
```

#### llama-cli

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3,4,6 \
./build/bin/llama-cli \
  -m /sdd2/official_weights/GLM-5.1-GGUF/UD-IQ2_XXS/GLM-5.1-UD-IQ2_XXS-00001-of-00006.gguf \
  --ctx-size 16384 \
  --temp 1.0 \
  --top-p 0.95 \
  -ngl 99 \
  -fa on
```

#### llama-server

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3,4,6 \
./build/bin/llama-server \
  -m /sdd2/official_weights/GLM-5.1-GGUF/UD-IQ3_S/UD-IQ3_S/GLM-5.1-UD-IQ3_S-00001-of-00007.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  --ctx-size 128000 \
  --temp 1.0 \
  --top-p 0.95 \
  -ngl 99 \
  -fa on
```

```bash
./build/bin/llama-server \
  -m /sdd2/official_weights/GLM-5.1-GGUF/UD-IQ3_S/UD-IQ3_S/GLM-5.1-UD-IQ3_S-00001-of-00007.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  --ctx-size 128000 \
  --temp 1.0 \
  --top-p 0.95 \
  -ngl 99 \
  -fa on \
  --parallel 8 \
  -t 32 \
  --batch-size 1024
```

### GPTOSS-120B-Uncensored-HauhauCS-Aggressive-MXFP4

```bash
CUDA_VISIBLE_DEVICES=4,5,6,7 \
/home/tangpp1/llama.cpp-master/build/bin/llama-server \
  -m /sdd2/official_weights/GPTOSS-120B-Uncensored-HauhauCS-Aggressive-MXFP4/GPTOSS-120B-Uncensored-HauhauCS-Aggressive-MXFP4.gguf \
  --host 0.0.0.0 \
  --port 5000 \
  --jinja \
  -fa on \
  -b 2048 \
  -ub 2048
```

### Qwen3.5-122B-A10B-Uncensored-HauhauCS-Aggressive-Q8_K_P

```bash
CUDA_VISIBLE_DEVICES=4,5,6,7 \
/home/tangpp1/llama.cpp-master/build/bin/llama-server \
  -m /sdd2/official_weights/Qwen3.5-122B-A10B-Uncensored-HauhauCS-Aggressive-Q8_K_P/Qwen3.5-122B-A10B-Uncensored-HauhauCS-Aggressive-Q8_K_P.gguf \
  --host 0.0.0.0 \
  --port 5000 \
  --jinja \
  -fa on \
  -b 2048 \
  -c 256000 \
  -ngl 99 \
  -ub 2048
```

### Qwen3.6-27B-Uncensored-HauhauCS-Aggressive-Q8_K_P

```bash
CUDA_VISIBLE_DEVICES=4,5 \
/home/tangpp1/llama.cpp-master/build/bin/llama-server \
  -m /sdd2/official_weights/qwen3.6gguf/Qwen3.6-27B-Uncensored-HauhauCS-Aggressive-Q8_K_P/Qwen3.6-27B-Uncensored-HauhauCS-Aggressive-Q8_K_P.gguf \
  --host 0.0.0.0 \
  --port 5000 \
  --jinja \
  -fa on \
  -b 2048 \
  -c 256000 \
  -ngl 99 \
  --reasoning-format none \
  -ub 2048
```

### vLLM 直接加载 Qwen3.6-27B

```bash
LD_LIBRARY_PATH="" \
CUDA_VISIBLE_DEVICES=4,5,6,7 \
vllm serve /sdd2/official_weights/qwen3.6gguf/Qwen3.6-27B-Uncensored-HauhauCS-Aggressive-Q8_K_P/Qwen3.6-27B-Uncensored-HauhauCS-Aggressive-Q8_K_P.gguf \
  --tokenizer /sdd2/official_weights/Qwen3.6-27B \
  --max-model-len 262144 \
  --host 0.0.0.0 \
  --port 5000 \
  --served-model-name Qwen3.6-27B \
  --tensor-parallel-size 4
```

### vLLM OpenAI API Server 加载 GLM-5.1 GGUF

```bash
python -m vllm.entrypoints.openai.api_server \
  --model /sdd2/official_weights/GLM-5.1-GGUF/UD-IQ3_S/UD-IQ3_S/ \
  --served-model-name glm-5.1 \
  --port 8080 \
  --tensor-parallel-size 8 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 32768 \
  --trust-remote-code \
  --dtype float16 \
  --disable-custom-all-reduce \
  --quantization gguf
```

### DeepSeek-V4-Flash

```bash
vllm serve /sdd2/official_weights/DeepSeek-V4-Flash \
  --trust-remote-code \
  --kv-cache-dtype fp8 \
  --block-size 256 \
  --tensor-parallel-size 8 \
  --tokenizer-mode deepseek_v4 \
  --tool-call-parser deepseek_v4 \
  --enable-auto-tool-choice \
  --served-model-name DeepSeek-V4-Flash \
  --reasoning-parser deepseek_v4 \
  --enforce-eager
```

### MiniMax-M2.7

```bash
SAFETENSORS_FAST_GPU=1 \
vllm serve /sdd2/official_weights/MiniMax-M2.7 \
  --trust-remote-code \
  --enable_expert_parallel \
  --tensor-parallel-size 8 \
  --enable-auto-tool-choice \
  --tool-call-parser minimax_m2 \
  --reasoning-parser minimax_m2_append_think \
  --served-model-name MiniMax-M2.7
```

### Qwen3.6-27B

```bash
LD_LIBRARY_PATH="" \
VLLM_USE_MODELSCOPE=true \
vllm serve /sdd2/official_weights/Qwen3.6-27B \
  --port 8000 \
  --tensor-parallel-size 4 \
  --max-model-len 262144 \
  --reasoning-parser qwen3 \
  --enable-auto-tool-choice \
  --served-model-name Qwen3.6-27B \
  --tool-call-parser qwen3_coder
```

---

## 媒体下载与转码

### 查看可下载格式

```bash
yt-dlp -F "https://youtu.be/MqsG3DVE2nA" \
  --extractor-args "generic:impersonate" \
  --cookies C:\Users\sheny\Downloads\cookies.txt
```

### 下载 YouTube 视频

```bash
yt-dlp -f 313+140 \
  "https://youtu.be/MqsG3DVE2nA" \
  --extractor-args "generic:impersonate" \
  --cookies C:\Users\sheny\Downloads\cookies.txt
```

原文另有一条带 cookies 的 `yt-dlp` 命令，但引号疑似被富文本替换，建议执行前先手动检查引号是否为标准 ASCII 引号。

### 音视频合流

```bash
ffmpeg -i "C:\Users\sheny\Downloads\videoplayback.webm" \
  -i "C:\Users\sheny\Downloads\videoplayback.m4a" \
  -c:v copy \
  -c:a copy \
  "C:\Users\sheny\Downloads\653.mkv"
```

### MOV 转 MP4

```bash
ffmpeg -i "F:\Leasure\褰辫鐗囨\宸茬煡\鐢熸棩蹇箰锛堟棤澹帮級.mov" \
  -c:v libx264 \
  -c:a aac \
  -b:a 192k \
  "C:\Users\sheny\Downloads\output.mp4"
```

### MKV 转 MP4

```bash
ffmpeg -i "F:\Leasure\妗堜欢.mkv" \
  -c:v copy \
  -c:a aac \
  -sn \
  "F:\Leasure\妗堜欢\澶╃綉.mp4"
```

### 重新编码压缩

```bash
ffmpeg -i "F:\Leasure\妗堜欢\澶╃綉.mp4" \
  -c:v libx264 \
  -crf 18 \
  -c:a copy \
  "F:\Leasure\妗堜欢\鍘熻棰?mp4"
```

### GPU 转码

```bash
ffmpeg -hwaccel cuda \
  -i "F:\Leasure\妗堜欢\\澶╃綉.mp4" \
  -c:v h264_nvenc \
  -pix_fmt yuv420p \
  -preset p4 \
  -rc vbr \
  -cq 18 \
  -b:v 0 \
  -c:a copy \
  "F:\Leasure\妗堜欢\\鍘熻棰慍UDA.mp4"
```

### 提取音频

```bash
ffmpeg -i "D:\WeChat\xwechat_files\wxid_4xyqbxgqh7jn22_6182\msg\video\2026-03\9f6e076fca64ed22cf3f633785ce27ab.mp4" \
  -vn \
  -acodec pcm_s16le \
  -ar 16000 \
  -ac 1 \
  C:\Users\nhsys\Music\test.wav
```

### 其他转码示例

```bash
ffmpeg -i "H:\Leasure\鍥藉唴\2KILL4\78.TwoGirlsDie2Cora&Ella-.rmvb" \
  -c:v libx264 \
  -c:a aac \
  "F:\datasets\output.mp4"
```

---

## WAN / 视频生成

### 文生视频

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3,6,7 \
torchrun \
  --nproc_per_node=8 \
  generate.py \
  --task t2v-A14B \
  --size 1280*720 \
  --ckpt_dir /sdd2/offical_weights/WAN2.2/Wan2.2-T2V-A14B \
  --dit_fsdp \
  --t5_fsdp \
  --ulysses_size 8 \
  --prompt "<prompt>"
```

### 图生视频

```bash
torchrun \
  --nproc_per_node=8 \
  generate.py \
  --task i2v-A14B \
  --size 1280*720 \
  --ckpt_dir /sdd2/offical_weights/WAN2.2/Wan2.2-I2V-A14B \
  --image /home/tangpp1/test_data/pic/20250923144656_682_34.jpg \
  --dit_fsdp \
  --t5_fsdp \
  --ulysses_size 8 \
  --prompt "<prompt>"
```

### Animate 预处理：动作驱动

```bash
python ./wan/modules/animate/preprocess/preprocess_data.py \
  --ckpt_path /sdd2/offical_weights/WAN2.2/Wan2.2-Animate-A14B/process_checkpoint/ \
  --video_path /home/tangpp1/test_data/animate_test/vd/real_hg_10s_1.mp4 \
  --refer_path /home/tangpp1/test_data/animate_test/pic/zhiyu_huisi1080.jpg \
  --save_path /home/tangpp1/projects/wan2.2/animate_preprocess/3 \
  --resolution_area 1280 720 \
  --retarget_flag \
  --use_flux
```

### Animate 预处理：替换

```bash
python ./wan/modules/animate/preprocess/preprocess_data.py \
  --ckpt_path /sdd2/offical_weights/WAN2.2/Wan2.2-Animate-A14B/process_checkpoint/ \
  --video_path /home/tangpp1/test_data/animate_test/vd/real_hg_2.mp4 \
  --refer_path /home/tangpp1/test_data/animate_test/pic/zhiyu_huisi1080.jpg \
  --save_path /home/tangpp1/projects/wan2.2/animate_preprocess/4 \
  --resolution_area 1280 720 \
  --iterations 3 \
  --k 7 \
  --w_len 1 \
  --h_len 1 \
  --replace_flag
```

### Animate 执行：动作驱动

```bash
python -m torch.distributed.run \
  --nnodes 1 \
  --nproc_per_node 8 \
  generate.py \
  --task animate-14B \
  --ckpt_dir /sdd2/offical_weights/WAN2.2/Wan2.2-Animate-A14B/ \
  --src_root_path /home/tangpp1/projects/wan2.2/animate_preprocess/3 \
  --refert_num 1 \
  --dit_fsdp \
  --t5_fsdp \
  --ulysses_size 8
```

### Animate 执行：替换

```bash
python -m torch.distributed.run \
  --nnodes 1 \
  --nproc_per_node 8 \
  generate.py \
  --task animate-14B \
  --ckpt_dir /sdd2/offical_weights/WAN2.2/Wan2.2-Animate-A14B/ \
  --src_root_path /home/tangpp1/projects/wan2.2/animate_preprocess/4 \
  --refert_num 1 \
  --replace_flag \
  --use_relighting_lora \
  --dit_fsdp \
  --t5_fsdp \
  --ulysses_size 8
```

---

## Ollama

```bash
ollama run qwen2.5 --keepalive -1
export OLLAMA_HOST=0.0.0.0
export OLLAMA_MODELS="/mnt/tmp/shenyh/ollama_weights"
sudo systemctl stop ollama
```

---

## 代理 / SSH 反向隧道

### SSH 反向隧道

```bash
ssh -o "IdentitiesOnly=yes" -R 7890:127.0.0.1:5188 tangpp1@10.10.11.22
ssh -o "IdentitiesOnly=yes" -R 7890:127.0.0.1:5188 shenyh@10.10.11.31
ssh -o "IdentitiesOnly=yes" -R 0.0.0.0:7890:127.0.0.1:5188 shenyh@10.10.11.31
ssh -o "IdentitiesOnly=yes" -R 7890:127.0.0.1:5188 chenyj@10.10.11.21
```

### 清理代理并重新设置

1. 清理 Git 全局代理

```bash
git config --global --unset http.proxy
git config --global --unset https.proxy
```

2. 清理当前 shell 环境变量

```bash
unset http_proxy
unset https_proxy
unset ALL_PROXY
```

3. 设置本地代理

```bash
export http_proxy="http://127.0.0.1:7890"
export https_proxy="http://127.0.0.1:7890"
```

4. 验证连通性

```bash
curl -Iv https://github.com
curl -Iv https://google.com
```

---

## Docker

### 常用命令

```bash
docker ps
docker ps -a
docker start my_hermes_v2
docker exec -it hermes-web-final /bin/bash
docker start -ai my_hermes_v2
```

### 启动容器

```bash
docker run -it -d \
  --name hermes-web-final \
  -p 8787:8787 \
  -v /mnt/tmp/shenyh/docker_mount:/app/ \
  hermes-ready:v2
```

---

## Hugging Face / 其他工具

### LLaMA Factory

```bash
llamafactory-cli webui
```

### Hugging Face 镜像与下载

```bash
export HF_ENDPOINT=https://hf-mirror.com
hf download HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive \
  mmproj-Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-f16.gguf \
  --local-dir /sdd2/official_weights/qwen3.6gguf
```

---

## Nginx

```powershell
.\nginx.exe -t
.\nginx.exe -s reload
```

---

## 敏感信息存放建议

原始文档里包含以下类型的敏感内容，建议不要继续直接写在通用手册中：

- OpenRouter API Key
- LangSmith Key
- 其他服务 Token / Cookie 文件路径

更稳妥的做法：

```bash
export OPENROUTER_API_KEY="<your_key>"
export LANGSMITH_API_KEY="<your_key>"
```

如果必须保留，建议单独拆到：

- `handbook.secrets.md`
- `.env`
- 密码管理器或安全笔记工具

---

## 备注

- 原文有部分中文注释出现乱码，本整理版保留了命令主体，并按上下文补了更清晰的分类标题。
- 原文里有少量重复命令，这里已去重或合并。
- 所有明确属于“同一条多行 Linux 命令”的内容，已统一补上续行反斜杠 `\`；单行命令保持原样，避免不必要的视觉噪音。
