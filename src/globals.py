'''
Keeps track of globally accesible objects and functions
Also contains a way to map from a rule_id to the handle_ids that suppor it

@author: diego
'''
from itertools import count
from orjson import orjson
import asyncio
import traceback

SESSION= None

RULES_HANDLE: dict[str, list[str]] = dict() # Contains a rule id and the handles that support it

### HANDLES
HANDLES=dict()

class Handle():
    '''Object for a file output as well as what rules it should pull'''
    iterator = count() # for handle id to make inter-relational datastructures lighter
    
    def __init__(self, name, file, rules=None): 
        self.name = name
        self.file = file
        self.__rules = list() if not rules else [get_rule_by_name(rule).id for rule in rules]
        self.__id=next(self.iterator)
        self.open_file=None
    
    @property
    def rules(self):
        '''list of rule ids'''
        return self.__rules
    
    @property
    def id(self):
        '''id of handle itself'''
        return self.__id
    
    def add_rules(self, rules):
        '''add rules by name to handle'''
        for rule in rules:
            rule_id = get_rule_by_name(rule).id
            if rule_id not in self.__rules:
                self.__rules.append(rule_id)
                
    def rem_rules(self, rules):
        '''remove rules by name from handle'''
        
        for rule in rules:
            rule_id = get_rule_by_name(rule).id
            if rule_id in self.__rules:
                self.__rules.remove(rule_id)
        
    def open_files(self):
        '''Opens up the file object for writing'''
        self.open=open(self.file, 'w', encoding="utf-8")
        
    def close_files(self):
        '''closes and releases file object'''
        self.open.close()
        
    def write(self, text):
        '''write a line of text'''
        self.open.write(text)
        self.open.write("\n")

def add_handle(handle: Handle):
    HANDLES[handle.id] = handle
    
def rem_handle(id: str):
    del HANDLES[id]
    
def get_handle_by_id(id):
    '''get's handle by id'''
    if id in HANDLES.keys():
        return HANDLES[id]
    else:
        return None
    
def get_handle_by_name(name):
    '''retrieves handle by name'''
    for handle in HANDLES.values():
        if handle.name == name:
            return handle
    return None


### RULES
RULES = dict()

def add_rule(rule):
    for x in RULES.values():
        if x.name == rule.name:
            rule.name+='(1)'
    
    if rule.id in RULES.keys():    
        x.name=rule.name
        x.value=rule.value
        x.tag = rule.tag
        return
    
    RULES[rule.id] = rule
    
def rem_rule(id):
    pass

def get_rule_by_name(name):
    for x in RULES.values():
        if x.name == name:
            return x
    
    return None

def get_rule_by_id(id):
    if id in RULES.keys():
        return RULES[id]
    return None

### GENERAL: 
__RUNNING=False

async def process_tweets(stream):
    ''' Waits for input from response stream, closing stream and returning when _RUNNING is False'''
    try:
        async for raw_response in stream.content:
            if raw_response.strip():
                
                response=orjson.loads(raw_response)
                
                handle_ls=list()
                for rule in response['matching_rules']:
                    if rule['id'] in RULES_HANDLE.keys():
                        handle_ls.extend(RULES_HANDLE[rule['id']])
                
                tweet = response['data']
                for handle in set(handle_ls):
                    if not __RUNNING:
                        stream.close()
                        await stream.release()
                        
                        return
                    get_handle_by_id(handle).write(orjson.dumps(tweet).decode("utf-8"))
            await asyncio.sleep(0)
    except Exception:
        traceback.print_exc() 

        
async def start(stream):
    '''First maps our rule_id and corresponding handle_ids in RULES_HANLDES
    Then it start process_tweets in a task
    '''
    for rule_id in RULES.keys():
        RULES_HANDLE[rule_id]=[]
    
    for handle in HANDLES.values():
        handle.open_files()
        
        for rule in handle.rules:
            RULES_HANDLE[rule].append(handle.id)
            
        if not handle.rules:
            for value in RULES_HANDLE.values():
                value.append(handle.id)
    global __RUNNING, work_thread 
    __RUNNING=True
    asyncio.get_event_loop().create_task(process_tweets(stream))
    
    
def close():
    '''closes the streaming operations'''
    global __RUNNING
    __RUNNING = False
    for handle in HANDLES.values():
        handle.close_files()
    
        
        