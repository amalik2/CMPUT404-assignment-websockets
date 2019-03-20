#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, request
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
app._static_folder = os.path.join(os.getcwd(), "static/")
sockets = Sockets(app)
app.debug = True

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

myWorld = World()        

# Credit to Umut for this: https://stackoverflow.com/a/47526225
sockets_list = []

def set_listener( entity, data ):
    ''' do something with the update ! '''
    for socket in sockets_list:
        if (socket.closed):
            sockets_list.remove(socket)
        else:
            raw_data = {}
            raw_data[entity] = data
            socket.send(json.dumps(raw_data))

myWorld.add_set_listener( set_listener )
        
@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    return app.send_static_file("index.html")

def read_ws(ws,client):
    '''A greenlet function that reads from the websocket and updates the world'''
    # XXX: TODO IMPLEMENT ME
    while not ws.closed:
        message = ws.receive()
        try:
            if message:
                message = json.loads(message)
                keys = message.keys()
                for key in keys:
                    myWorld.set(key, message[key])
        except Exception as e:
            print(message)
            print(e)
        #print(message)
        #ws.send(message)
    return None

@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    # XXX: TODO IMPLEMENT ME
    sockets_list.append(ws)
    ws.send(json.dumps(myWorld.world()))
    read_ws(ws, None)

# I give this to you, this is how you get the raw body/data portion of a post in flask
# this should come with flask but whatever, it's not my project.
def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data.decode("utf8") != u''):
        return json.loads(request.data.decode("utf8"))
    else:
        return json.loads(request.form.keys()[0])

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    data = flask_post_json()
    myWorld.set(entity, data)
    return Response(json.dumps(data), status=200, mimetype="application/json")

@app.route("/world", methods=['POST','GET'])    
def world():
    '''you should probably return the world here'''
    return esponse(json.dumps(myWorld.world()), status=200, mimetype="application/json")

@app.route("/entity/<entity>")    
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
    data = myWorld.get(entity)
    status = 200
    if (data == None):
        status = 404
    return Response(json.dumps(data), status=status, mimetype="application/json")


@app.route("/clear", methods=['POST','GET'])
def clear():
    '''Clear the world out!'''
    myWorld.clear()
    return Response(json.dumps(myWorld.world()), status=200, mimetype="application/json") 



if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    #app.run()
    # Credit to https://github.com/heroku-python/flask-sockets (MIT License)
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    server = pywsgi.WSGIServer(('', 5000), app, handler_class=WebSocketHandler)
    server.serve_forever()
