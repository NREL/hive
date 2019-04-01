import subprocess
import os.path

def run_actions(actions, target=None):
    if target == None:
        subprocess.run(actions)
    else:
        with open(target, 'w') as f:
            subprocess.run(actions, stdout=f)

def task_setup():
    if not os.path.exists('config.py'):
        for actions, name in [('cp config.default.py config.py', 'create config from default'), ('rm config.default.py', 'remove default config')]:
            yield {
                    'name': name, 
                    'actions': [actions],
                    }
    else:
        print("Already Setup")

def task_update_deps():
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
