import os
import yaml

import cerebras_pytorch as cstorch
import torch

from model import StandardCosmoFlow
from data import get_train_dataloader

def main(cs_config):
    with open("./params.yaml", "r") as stream:
        params = yaml.safe_load(stream)
    
    model = StandardCosmoFlow()
    backend = cstorch.backend("CSX", use_cs_grad_accum=False, compile_dir="/home/z043/z043/crae-cs1/chris-ml-intern/cs2/ML_HPC/CosmoFlow/comp_path")
    compiled_model = cstorch.compile(model, backend=backend)

    optimizer = cstorch.optim.SGD(model.parameters(), lr=0.001, momentum=0.9)

    cerebras_loader = cstorch.utils.data.DataLoader(get_train_dataloader, params)

    criterion = torch.nn.MSELoss()
    
    @cstorch.trace
    def train_step(x, y):
        logits = compiled_model(x)
        loss = criterion(logits, y)

        loss.backward()
        optimizer.step()
        optimizer.zero_grad()
        cstorch.summarize_scalar("loss", loss)
        return loss
    writer = cstorch.utils.tensorboard.SummaryWriter()
    executor = cstorch.utils.data.DataExecutor(cerebras_loader, num_steps=params["runconfig"]["max_steps"], checkpoint_steps=params["runconfig"]["checkpoint_steps"], cs_config=cs_config, writer=writer)

    for x, y in executor:
        loss = train_step(x, y)

def get_default_inis():
    return {
        "ws_cv_auto_inis": True,
        "ws_opt_target_max_actv_wios": 16,
        "ws_opt_max_wgt_port_group_size": 8,
        "ws_run_memoize_actv_mem_mapping": True,
        "ws_opt_bidir_act": False,
        "ws_variable_lanes": True,
    }

if __name__ == "__main__":
    #debug_args = DebugArgs()
    #set_default_ini(debug_args, **get_default_inis())
    #write_debug_args(debug_args, os.path.join(os.getcwd(), ".debug_args.proto"))

    cs_config = cstorch.utils.CSConfig(
        mount_dirs=["/mnt/e1000/home/z043/z043/crae-cs1/chris-ml-intern/cs2/modelzoo", os.getcwd()],
        python_paths=[os.getcwd()],
        max_wgt_servers=1,
        num_workers_per_csx=1,
        max_act_per_csx=1,
        
        #precision_opt_level=0
        #debug_args=debug_args
    )

    main(cs_config)