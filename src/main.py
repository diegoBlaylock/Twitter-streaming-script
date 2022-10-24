'''
Created on Oct 18, 2022

@author: diego
'''
from sys import argv
import getpass
import sys
import os
import asyncio
import globals
from typing import Any
from net import utils
from command.commands import Handler
from command import basic_commands
from net.utils import Unauthorized



def dec_input() -> Any:
    '''add decoration before input()'''
    print(">>>>>>>> ", end = "")
    return input()

def get_bearer_token()-> str:
    '''Asks for bearer_tokens'''
    print("Use help for info\n"
          "Enter Bearer token to start (type 'secret' to hide input, or env for variable):")
    
    inp = dec_input().strip()
    
    match inp.lower():
        case 'secret':
            
            inp = getpass.getpass("> ", sys.stdout)
        case 'env':
            inp = os.environ[dec_input().strip()]
                
    
    return inp


async def start(bearer_token: str):
    '''The start coroutine to begin all the asynchronous function'''
    print("Ready")
    
    globals.SESSION = await utils.TwitterSession(bearer_token)
    handle = Handler() 
    basic_commands.setup(handle)
    await basic_commands.sync_rules() #IMPORTANT: synchronize the rules that twitter has
    
    while not globals.SESSION.closed:
        await handle._handle(dec_input())
        print()
        
if __name__ == '__main__':

    if len(argv)>1:
        '''This is meant for file input of a script. TODO'''
        try:
            x=argv.index('-f')
            if len(argv) <= x+1:
                print("Use the -f flag before your file arguments")
                exit()
            
            path=argv[x+1]
            try:
                open(path, 'r')
                #TODO
            except FileNotFoundError:
                print("Couldn't find file: {}".format(path))
        except ValueError as e:
            print("Use the -f flag before your file arguments")
            exit()
            
    else:
        def try_bearer_token():
            '''Used for repeatedly asking for a token until a valid one is given'''
            try:
                bearer_token = get_bearer_token()
                print("Loading bearer token\n")
                asyncio.run(start(bearer_token))
            except Unauthorized:
                print("Couldn't get authorized with Bearer Token, Try again")
                try_bearer_token()
        
        try_bearer_token()