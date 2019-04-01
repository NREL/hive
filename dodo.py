import subprocess
import os.path

DOIT_CONFIG = {
        'default_tasks': [],
        }

def run_actions(actions, target=None):
    if target == None:
        subprocess.run(actions)
    else:
        with open(target, 'w') as f:
            subprocess.run(actions, stdout=f)

def task_setup():
    """
    Setup project from sratch. WARNING: This overwrites your config file with defaults.
    """
        
    for name, dep, actions, targets in [
            ('create config from default', 'config.default.py', 'cp config.default.py config.py', 'config.py'), 
            ]:
        yield {
                'name': name, 
                'actions': [actions],
                'file_dep': [dep],
                'targets': [targets],
                }

def task_update_deps():
    """
    Update conda environment.yml file and pip requirements.txt file.
    """
    for target, actions in [
            ('environment.yml', ['conda', 'env', 'export', '-n', 'mist']),
            ('requirements.txt', ['pip', 'freeze']),
            ]:
        yield {
                'name': target,
                'actions': [(run_actions, [actions, target])],
                'targets': [target],
                'clean': True,
                }

