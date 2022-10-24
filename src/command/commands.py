'''
An abstraction for the command and arguments put in to the console

@author: diego
'''
from typing import Union, Optional
import typing
from dataclasses import dataclass

@dataclass
class Command:
    '''Wraps a callable with a name and a description'''
    name: str
    handler: typing.Callable
    description: str = "..."
    
    async def __call__(self, *args, **kwargs):
        '''Ports argument into a call to the callable'''
        try:
            await self.handler( *args, **kwargs)
        except TypeError as e: #If the arguments don't match the callables argument list, this catchSs it
            print(f'Incorrect Usage: {self.name} {self.get_params()}')
            
    def get_params(self):
        '''Uses function annotations to return a parameter string'''
        return " ".join([f"<{k}>" if (not (v is Optional or (v is Union and v.__args__[1] is None))) else f"[opt: {k}]" for k, v in self.handler.__annotations__.items() if k != "return"])
    
    def get_help(self):
        return f"{self.name} {self.get_params()} : {self.description}"
    
    @staticmethod
    def command(*, name = None, description = None, handler=None):
        '''A decorator, returning a function as a Command'''
        
        def decorator(fn):
            nonlocal description
            nonlocal name
            
                
            if not name:
                name = fn.__name__
                
            comm= Command(name=name, handler = fn, description=description)
            if handler:
                handler.add_command(comm)
                
            return comm
        return decorator
   
    
def get_next(generator: typing.Generator):
    '''A wrapper for next() that returns None at the end of iteration
    instead of throwing StopIteration
    '''
    try:
        return next(generator)
    except StopIteration:
        return None

def _splinter(string: str):
    '''Does preproccessing on the input from user, creating an iterator with each seperate token'''
    sum = ""
    is_qouted=None
    escape = False
    
    for char in string:
        if char=='\\':
            escape=True
            continue
        
        if not escape and (char == '"' or char == "'"):
            if is_qouted and is_qouted==char:
                is_qouted=None
            elif is_qouted:
                sum+=char
            else:
                is_qouted=char
        elif char.isspace() and not is_qouted:
            if len(sum)>0:
                yield sum
                sum = ""
            pass
        else:
            sum+=char
        
        escape = False    
    if len(sum) > 0: yield sum
    
        
    
    
    
class Handler():
    '''Used to register commands and to create a description for the help function'''
    def __init__(self):
        self.commands: dict[str, Union[typing.Callable, Handler]]=dict()
        self.add_command(self.help)
        
    def _check_command(self, command: str):
        if command not in self.commands.keys():
            raise InvalidCommand
        
    async def _handle(self, input: typing.Generator[str, None, None]):
        '''Used to handle user input and distribute them to the handles underlying commands'''
        input = _splinter(input)
        command = get_next(input) #First token in input
        
        if command is None: #Input empty
            await self.help()
            return
        
        try:
            self._check_command(command) # is valid command?
        except InvalidCommand:
            print(f"sorry, I don't recognize '{command}' as a command")
            return
        
        
        if isinstance(self.commands[command], CommandGroup):
            await self.commands[command]._handle( input) # gives command group a stream as input
        else:
            await self.commands[command](self, *list(input)) # gathers the rest of the stream as arguments
    
    def add_command(self, command: Command):   
        self.commands[command.name] = command
        
    def add_group(self, group):
        group.setup(self)
        self.commands[group.name] = group
            
    def get_help(self, recurse = False):
        '''Create help string, recurse = verbose'''
        ls = list()
        for command in self.commands.values():
            if isinstance(command, CommandGroup):
                if recurse:
                    for x in command.get_help(True):
                        ls.append(f"\t{x}")
                else:
                    for x in command.get_simple_help():
                        ls.append(f"\t{x}")
            else:
                ls.append(f"\t{command.get_help()}")
        return ls
    
    
    @Command.command( description="Help Function")
    async def help(self, r_flag: Optional=False):
        print("Here are your commands:\n"+"\n".join(self.get_help(r_flag=='-r')))
    

class CommandGroup(Handler):
    '''This groups commands and prefixes them with another command'''
    def __init__(self, description=None):
        
        self.name = self.__class__.__name__
        self.description = description
        Handler.__init__(self)

        #self.add_command(self.help)
        
    async def _handle(self, input):
        '''handle input stream'''
        command = get_next(input)
        
        if command is None:
            await self.help(self)
            return
        
        try:
            self._check_command(command)
        except InvalidCommand:
            print(f"sorry, I don't recognize '{command}' as a command")
            return
        
        
        if isinstance(self.commands[command], CommandGroup):
            await self.commands[command]._handle( input)
        else:
            await self.commands[command](self, *list(input))
            
    def setup(self, handler):        
        pass
    
    def add_command(self, command: Command):
        Handler.add_command(self, command)
        command.name = f"{self.name} {command.name}"
    
    def get_help(self, recurse: bool = False):
        "Get entire help string"
        ls = [f"{self.name} ... : {self.description}",]
        for command in self.commands.values():
            if isinstance(command, CommandGroup):
                if recurse:
                    
                    for x in command.get_help(True):
                        ls.append(f"\t{x}")
                else:
                    for x in command.get_simple_help():
                        ls.append(f"\t{x}")
            else:
                ls.append(f"\t{command.get_help()}")
        return ls
            
    def get_simple_help(self):
        '''return a simplied string for parent handler's help functions'''
        return [f"{self.name} ... : {self.description}"]
    
    @Command.command(description="Help Function")
    async def help(self, r_flag: Optional=False):    
        print(f"Here are your commands for {self.name}:\n"+"\n".join(self.get_help(r_flag=='-r')))
        
class InvalidCommand(BaseException):
    pass    