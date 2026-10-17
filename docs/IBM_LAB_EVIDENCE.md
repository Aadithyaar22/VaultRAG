# IBM Z / LinuxONE AI/ML lab — evidence (run 2026-10-17 on our instance)

Followed IBM's "Running AI/ML in Jupyter Lab on IBM LinuxONE" guide on our LinuxONE Community Cloud instance
(`hacktivists`, IP 148.100.99.19, Ubuntu 24.04.5, **s390x**, 3 vCPU, 7 GB RAM).

| Guide step | What we did |
|---|---|
| Instance + SSH key | Created (portal), key pair `hacktivists` |
| Install Docker | `docker.io` from Ubuntu's repo (Docker 29.1.3, s390x) — instead of the `get.docker.com` pipe-to-shell script |
| Pull image | `registry.linuxone.cloud.marist.edu/l1cc/jupyterlab-image-s390x:latest` (9.85 GB) |
| Start container | `docker run --network host --name notebook -v ~/shared:/home/ibm-user/shared …` on port 38888 |
| Token | **Random strong token** instead of the default `Your_Token1`; `allow_origin='*'` **not** set |
| Firewall (port 38888) | **Deliberately not opened** (Jupyter = code execution). Access is via SSH tunnel: `ssh -N -L 38888:127.0.0.1:38888 -i <key> linux1@148.100.99.19` → http://localhost:38888 |
| Notebooks 1–4 | Executed headless with `jupyter nbconvert --execute` (exit 0, no error outputs); executed copies kept outside the repo (IBM-provided content) |

## Hardware check (our own, from `/proc/cpuinfo`)
Machine type **9175 (IBM z17)**; CPU features include `vxe2`, `dflt`, **`nnpa`** (Telum II on-chip AI accelerator), `sie`.

## Results (as printed by the notebooks on this instance)
| Notebook | Run time | Result |
|---|---|---|
| `Churn_Scikit_PyTorch` | 13 s | Trained on 4,800 / tested on 1,201 customers; PyTorch test accuracy ended ≈73% (peaked ≈79% mid-training) |
| `Fraud_LSTM_Keras_TF` | 102 s | LSTM fraud model: TP=3 FP=5 FN=0 TN=1992 (precision 0.375, recall 1.0); exported `fraud_lstm.onnx`; notebook-measured inference ≈4,833 sequences/s |
| `Digit_Class_TensorFlow` | 28 s | MNIST DNN exported (SavedModel/ONNX); notebook-measured inference ≈217,736 images/s (median 4.59 ms / 1000 images) |
| `Loan_Approval_Demo` | 68 s | Hybrid ML + RAG + `llama.cpp` (Granite model file in the container): risk model P(low risk)=0.997 → "Approve" with generated rationale |

## Caveats (read before quoting)
- Throughput/latency figures are what the lab notebooks printed; we did not independently benchmark them. The notebooks'
  text about which ops are "accelerated by NNPA" is explanatory output; we have not independently verified accelerator use.
- Our own VaultRAG models (scikit-learn: document classifier, injection classifier, IsolationForest) run on CPU and do
  **not** use the NNPA accelerator. Moving them to a TensorFlow/ONNX path that can use it is future work.
- The loan notebook warns that the container's Granite file (`granite-4.0-h-350m-base`) differs from the model it expects
  (`granite-3.3-2b-instruct`); we did not evaluate generation quality.
