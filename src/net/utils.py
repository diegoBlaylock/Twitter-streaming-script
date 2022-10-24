'''
Created on Oct 17, 2022

@author: diego
'''
import sys
from aiohttp.client_reqrep import ClientResponse
from dataclasses import dataclass
from aiohttp import ClientSession
from collections import deque
from orjson import dumps
from importlib import reload
from itertools import count

import asyncio
import os

rules_count = count() #Counter for rules' names

@dataclass(repr = False, init=False)
class Rule():
    '''Represent the Rule object'''
    
    def __init__(self, rules: str, tag:str="...", name=None, id=None):
        self.rules = rules
        self.tag = tag
        self.name = name if name else f"Rule{next(rules_count)}"
        self.id = id
        
    @staticmethod
    def from_scheme(*, scheme: list = None, string: str=None, tag=None):
        '''Reads a 'scheme text and outputs a text readable for twitter'''
        depth=-1
        
        def __cdr(inp: list)->list:
            return inp[1:]
        
        def __handle(inp: list)->list:
            
            if not isinstance(inp, (list, tuple, set)):
                return inp
            
            if inp:
                
                command = inp[0]
                
                match command:
                    case 'AND':
                        return __and(__cdr(inp))
                    case 'OR':
                        return __or(__cdr(inp))
                    case '-':
                        return neg(__cdr(inp))
                    case _:
                        return __and(inp)
            
            
        def __and(param):
            nonlocal depth
            depth+=1
            
            
            output = " ".join([__handle(string) for string in param])
            
            if depth>0:
                output = '({})'.format(output)
            
            depth-=1
            
            return output
        
        def __or(param):
            nonlocal depth
            depth+=1
            
            output = " OR ".join([__handle(x) for x in param])
            
            if depth>0:
                output = '({})'.format(output)
            
            depth-=1
            return output
            
        def neg(param):
            return " ".join([f"-{__handle(string)}" for string in param])
        if string:
            def __str2list(string):
                state = deque() #0 = list #1 = str
                
                output: list = None
                
                for char in string:
                
                        match char:
                            case "(":
                                ls = list()
                                if state and state[0] is not None:
                                    state[0].append(ls)
                                    state.appendleft(ls)
                                else:
                                    output = ls
                                    state.appendleft(ls)
                            case ")":
                                
                                if isinstance(state[0], str):
                                    string = state.popleft()
                                    state[0].append(string)
                                    state.popleft()
                                else:
                                    state.popleft()
                                    if not state:
                                        return output
                                
                            case _:
                                
                                if state and isinstance(state[0], str):
                                    if char.isspace():
                                        if state and isinstance(state[0], str):
                                            string = state.popleft()
                                            if not state:
                                                return string
                                            state[0].append(string)
                                    else:
                                        if state and isinstance(state[0], str):
                                            state[0]+=char
                                else:
                                    if char.isspace():
                                        pass
                                    else:
                                        state.appendleft(char)
                return output
            
            return Rule(__handle(__str2list(string)), tag = tag)
        else:               
            return Rule(__handle(scheme), tag = tag)
        
    def from_json(self, json):
        '''TODO'''
        pass
    def __repr__(self):
        '''String repr'''
        return f'{{"name": {self.name}, "id": {self.id}, "value":{self.rules}, "tag":{self.tag}}}'
    
    def __str__(self):
        return self.__repr__()
    
    def json(self):
        '''returns json respresentation'''
        return {"value":self.rules, "tag":self.rules}

def _check_add_rules(status: int, json):
    '''when adding rules, the response is sent here and will throw custom exceptions if an error occured'''
    match status:
        case 200:
            if "errors" in json.keys():
                if 'errors' in json['errors'][0].keys():
                    raise RuleNotFound()
                n='\n'
                raise InvalidRule(f"{json['errors'][0]['value']}: {n.join(json['errors'][0]['details'])}")
            #{"meta":{"sent":"2022-10-21T02:28:50.784Z","summary":{"created":0,"not_created":1,"valid":0,"invalid":1}},"errors":[{"value":"--b","details":["Rules must contain a non-negation term (at position 1)","Rules must contain at least one positive, non-stopword clause (at position 1)"],"title":"UnprocessableEntity","type":"https://api.twitter.com/2/problems/invalid-rules"}]}

        case 201:
            if 'errors' in json.keys():
                raise DuplicateRule("")
        case 401:
            raise Unauthorized()
        
        
class TwitterSession():
    '''Encapsulates the networking with Twitter'''
    
    
    async def __init__(self, token):
        self._d_header = {"content-type":'application/json', "Authorization" : f"Bearer {token}"}
        session = ClientSession("https://api.twitter.com" , headers = self.default_headers)
        self.session: ClientSession = session
        self.token=token
        await self.validate_token()
        
    async def __new__(cls, *args, **kwargs):
        '''Custom instanstiation to handle an asynchornous init function'''
        instance = super(TwitterSession, cls).__new__(cls)
        await instance.__init__(*args, **kwargs)
        return instance
    
    @property
    def default_headers(self):
        return self._d_header
    
    async def validate_token(self):
        '''Throws Unauthorized exception if bearer token is not accepted by Twitter'''
        resp = await self.session.get('/2/tweets/search/stream/rules')
        
        if resp.status == 401 and (await resp.json())["title"]=='Unauthorized':
            raise Unauthorized(self.token)
    
    async def modify_rules(self,*, add = None, delete=None):
        '''Allows one to add or delete rules in the Twitter Server'''
        payload = dict()
        
        if add is not None: # add 'add' value to payload along with rules to be added
            payload['add'] = list()
            
            for rule in add:
                payload['add'].append(rule.json())
        
        if delete is not None: # add delete value in payload json with ids to be deleted
            payload['delete'] = {"ids": (delete)}        
            
        resp =  await self.session.post('/2/tweets/search/stream/rules', data=dumps(payload))
        
        _check_add_rules(resp.status, await resp.json())
        
        resp = await resp.json()
        
        if add is not None: # used to backfill the id of the rules sent to add
            for rule_json in resp['data']:
                for rule in add:
                    if rule.rules == rule_json['value']:
                        rule.id = rule_json['id']
        return resp
        
    async def get_rules(self ):
        '''Fetch rules from the server'''
        resp = await self.session.get('/2/tweets/search/stream/rules')
        return (await resp.json())
        
    async def remove_all_rules(self):
        '''helper function to delete all rules'''
        resp = await self.get_rules()
        ls = []
        if resp['meta']['result_count']==0:
            return
        
        for rule in resp['data']:
            ls.append(rule['id'])
        
        return(await self.modify_rules(delete = ls))    
        
    async def close(self):
        '''closes ClientSession'''
        if not self.session.closed:
            await self.session.close()
            
    async def stream(self, timeout):
        '''return filtered stream with specified timeout'''
        params = {"tweet.fields" :"author_id,text","media.fields":"url"}
        
        if hasattr(self, '_stream'): # Caches stream, because stream would delay closing.
            resp = getattr(self, '_stream')
            
            if resp.closed:
                delattr(self, '_stream')
                return self.stream(timeout)
        else:
            resp: ClientResponse = await self.session.get('/2/tweets/search/stream', params = params, timeout=timeout)
            
            setattr(self, '_stream', resp)
            return resp
       
    @property
    def closed(self):
        return self.session.closed
    
class RuleNotFound(BaseException):
    '''When deleting, this will be thrown if an id doesnt exist int their DB'''
    pass

class RulesCapExceeded(BaseException):
    '''Tokens are allowed a specific amount of rules'''
    pass

class Unauthorized(BaseException):
    '''Bearer Token doesn't work'''
    pass

class InvalidRule(BaseException):
    '''Rule syntax is incorrect'''
    pass
class DuplicateRule(InvalidRule):
    '''Rule duplicate exists'''
    pass