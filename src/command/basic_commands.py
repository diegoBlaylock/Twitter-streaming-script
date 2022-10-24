'''
Created on Oct 19, 2022

@author: diego
'''

from command import commands
from command.commands import Command, CommandGroup
from net.utils import Rule, RulesCapExceeded, DuplicateRule, InvalidRule
from pprint import pprint
import globals

from typing import Optional
import itertools

async def sync_rules():
    '''grabs and compares rules from server and locally
    automatically fetches rules, but pushing rules is still
    to be implemented
    
    return the descrepencies
    '''
    
    ls = (await globals.SESSION.get_rules())['data']
    pulls = list()
    pushs = list()
    pushs.extend([rule.id for rule in globals.RULES.values()])
    
    for x in ls:
        if x['id'] in globals.RULES.keys():
            try: 
                pushs.remove(x['id'])
            except ValueError: pass
            
            globals.RULES[x[id]].rules = x['value']
            globals.RULES[x[id]].tag = x['tag']
        else:
            pulls.append(Rule(rules=x['value'], tag=x['tag'], id=x['id']))
            globals.add_rule(pulls[-1])
    return pulls, pushs

class rules(commands.CommandGroup):
    '''Access and modify current rules'''
    
    def __init__(self):
        CommandGroup.__init__(self, "Utility to modify the rules of the stream")
        self.add_command(self.add)
        self.add_command(self.delete)
        self.add_command(self.view)
        self.add_command(self.list)
        
            
    @Command.command(description="Add a rule to the stream")
    async def add(self, name: str, rule: str, tag: Optional=None):
        rule = Rule(rules = rule, tag = tag, name=name)
        
        try:
            await globals.SESSION.modify_rules(add=[rule])
            globals.add_rule(rule)
            
            print("")
        except InvalidRule as i:
            print("Couldn't add rule, invalid syntax:")
            pprint(str(i))
        except DuplicateRule as d:
            print("A duplicate was found, rule not added")
        except RulesCapExceeded as r:
            print("Rules cap exceeded, rule couldn't be added. Either delete rule or change bearer token")
        else:
            print("Rule succesfully add. Look at current rules with 'rules list'")
        
            
    @Command.command(description='Remove a rule from the stream')
    async def delete(self, name:str):
        rule = globals.get_rule_by_name(name)
        
        if name == "*":
            await globals.SESSION.remove_all_rules()
            globals.RULES.clear()
            return
        
        if rule is None:
            print("Rule {} doesn't exist".format(name))
            return
        
        await globals.SESSION.modify_rules(delete=[rule.id])
        globals.rem_rule(rule.id)
        
        print("Rule deleted")
        
    @Command.command(description='View a rule by name or id with -i before argument EX: rule view -i 12345')
    async def view(self, name:Optional, id:Optional=None):
        rule = None
        
        
        if name=='-i':
            if id is None:
                print("You need an id with '-i' flag")
                return
    
            rule = globals.get_rule_by_id(id)
                    
            if rule is None:
                print("Couldn't find rule with id {}".format(id))
                return
            
        else:
            rule = globals.get_rule_by_name(name)
            if rule is None:
                print("Couldn't find rule with name '{}'. Use 'rules list' to see current rules".format(name))
                return
        
        print("Rule '{}':"
              "\n\tID: {}"
              "\n\tfilter: {}"
              "\n\ttag: {}"
              "".format(rule.name, rule.id, rule.rules, rule.tag))
            
    @Command.command(description="Lists rules")
    async def list(self):
        print("\n".join(sorted([f"\t{x.name}: '{x.rules}'    <TAG:> '{x.tag}' {{{x.id}}}" for x in globals.RULES.values()])))
    
    @Command.command(description="Syncs the rules with the Twitter Server")
    async def sync(self):
        pass #TODO
       
class handle(commands.CommandGroup):
    
    def __init__(self):
        CommandGroup.__init__(self, "Utility to modify the rules of the stream")
        self.add_command(self.add)
        self.add_command(self.delete)
        self.add_command(self.view)
        self.add_command(self.list)
        self.add_command(self.file)
        self.add_group(self.rules())
    
        
    @Command.command(description="Adds a file output for the stream")
    async def add(self, name: str, file: str, *rules):
        globals.add_handle(globals.Handle(name, file, rules))
        print("Handle added...")
        
    @Command.command(description="Delete a handle")
    async def delete(self, name: str):
        globals.rem_handle(globals.get_handle_by_name(name).id)
        print('Handle deleted...')
        
    @Command.command(description="View the file handle")
    async def view(self, name: str):
        
        handle = globals.get_handle_by_name(name)
        if handle is None:
            print("Couldn't find handle with name '{}'. Use 'rules list' to see current rules".format(name))
            return
        
        print("Handle '{}':"
              "\n\tFILE: '{}'"
              "\n\tRULES:\t{}"
              "".format(handle.name, handle.file, ", ".join([f"{globals.get_rule_by_id(id).name}" for id in handle.rules]) \
                        if handle.rules else 'ALL'))
            
    @Command.command(description="Add a rule to the stream")
    async def list(self):
        ls = sorted([f"\t{x.name}: '{x.file}'" for x in globals.HANDLES.values()])
        if ls:
            print("\n".join(ls))
        else:
            print('EMPTY')
    @Command.command(description="Adds a file output for the stream")
    async def file(self, name: str, file: str):
        globals.get_handle_by_name(name).file = file
        print("Updated handle...")
        
    class rules(CommandGroup):
        def __init__(self):
            CommandGroup.__init__(self, "Add and Remove Rules from handlers")
            self.add_command(self.add)
            self.add_command(self.delete)
            
        @Command.command(description="Add rules to handle, use delete ALL to receive all")
        async def add(self, name:str, *rules: str):  
            globals.get_handle_by_name(name).add_rules(rules)
            print("Rule added to handler {}".format(name))
        @Command.command(description="Delete rules from a handle")
        async def delete(self, name:str, *rules: str):
            globals.get_handle_by_name(name).rem_rules(rules)
            print("Rule removed from handler {}".format(name))
            
@Command.command(description="start streaming to iterators")
async def stream(handler, hours=0, minutes=0, seconds=0):
    '''prints stream to handles'''
    total = (int(hours)*60 + int(minutes))* 60 +int(seconds)
    stream = await globals.SESSION.stream(total+5)
    
    # asyncio task is created allowing the program to continue
    # here and jumps between both coroutines with asyncio.sleep
    await globals.start(stream) 
    
    import asyncio
    import time
    
    cycle = itertools.cycle(('|', '/', '—', '\\'))
    proj_time = time.time() + total
    while time.time() < proj_time:
        
        print(next(cycle), end=chr(8))
        await asyncio.sleep(0.6)
        
    globals.close() #End

def setup(handler):
    '''Add all commands to handler'''
    handler.add_group(rules())
    handler.add_group(handle())
    handler.add_command(stream)


