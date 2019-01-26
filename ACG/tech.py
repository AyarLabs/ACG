"""
When imported, this module will extract tech information for easy access from a module specified by the 'ACG_TECH'
environment variable
"""
import yaml
import os

path = os.environ['ACG_TECH']
with open(path, 'r') as f:
    tech_info = yaml.load(f)
