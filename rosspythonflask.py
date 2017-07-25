#from flask_script import Manager, Server
from flask import Flask, url_for, request, make_response
import json
from cloudant.client import Cloudant
import numpy as np
import operator
import os
from cfenv import AppEnv
import urllib2
import requests
from datetime import timedelta
from functools import update_wrapper



app = Flask(__name__)

@app.route('/')
def api_root():
    return 'Welcome'


def crossdomain(origin=None, methods=None, headers=None, max_age=21600,attach_to_all=True, automatic_options=True):
    """Decorator function that allows crossdomain requests.
      Courtesy of
      https://blog.skyred.fi/articles/better-crossdomain-snippet-for-flask.html
    """
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        """ Determines which methods are allowed
        """
        if methods is not None:
            return methods

        options_resp = app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        """The decorator function
        """
        def wrapped_function(*args, **kwargs):
            """Caries out the actual cross domain code
            """
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers
            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            h['Access-Control-Allow-Credentials'] = 'true'
            h['Access-Control-Allow-Headers'] = \
                "Origin, X-Requested-With, Content-Type, Accept, Authorization"
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator

@app.route('/google', methods=['GET', 'POST', 'OPTIONS'])
@crossdomain(origin='*')
def api_google():
    if "text" in request.args:
        query = request.args['text']
        url = "http://google.com/complete/search?output=toolbar&q=" + query
        response = requests.get(url)
        retVal = response.content
        print retVal
        return retVal
    else:
        return "add a 'text' query string"


@app.route('/dota')
def api_dota():
    if 'heroes' in request.args:
        def getRecs(heroNames):
            cloudantCred = {
              'username':'c0d2f661-5249-4746-9936-c2b8e766c117-bluemix',
              'password':"""e2c7f4123d3f7a026373ca59f7d49b0e6e91fd76a47c741840da9b2585739c7c""",
              'host':'c0d2f661-5249-4746-9936-c2b8e766c117-bluemix.cloudant.com',
              'port':'443',
              'url':'https://c0d2f661-5249-4746-9936-c2b8e766c117-bluemix:e2c7f4123d3f7a026373ca59f7d49b0e6e91fd76a47c741840da9b2585739c7c@c0d2f661-5249-4746-9936-c2b8e766c117-bluemix.cloudant.com'
            }


            client = Cloudant(cloudantCred['username'],
                              cloudantCred['password'],
                              url=cloudantCred['url'],
                              connect=True)

            heroFeatDb = client['herofeatures']
            heroFeatDoc = heroFeatDb['recid']


            pf_keys = json.loads(
                heroFeatDoc.get_attachment('hero_feature_keys', attachment_type='text')
            )

            pf_vals = json.loads(
                heroFeatDoc.get_attachment('hero_feature_vals', attachment_type='text')
            )

            dotaSchema = json.loads(
                heroFeatDoc.get_attachment('dotaHeroschema', attachment_type='text')
            )
            my_database = client['dotaschema']
            my_document = my_database['66c6b76b9a3ac0c22d74b60d8c04ea65']

            heroids = []
            for hero in my_document['heroes']:
                if any(hero['name'] in s for s in heroNames):
                    heroids.append(str(hero['id']))

            Vt = np.matrix(np.asarray(pf_vals))

            full_u = np.zeros(len(pf_keys))

            heroes = {}
            schema = dotaSchema.split()
            heroes[8] = 0
            for col in schema:
                if col != "id" and col != "index":
                    if col in heroids:
                        print col
                        heroes[int(col)] = 1
                    else:
                        heroes[int(col)] = 0

            for key, value in heroes.items():
                idx = pf_keys.index(key)
                full_u.itemset(idx, value)

            recommendations = full_u*Vt*Vt.T

            recommendations = recommendations.tolist()[0]

            recDic = {}
            for heroInfo in my_document['heroes']:
                recDic[heroInfo['name']] = recommendations[int(heroInfo['id'])-1]

            sortedRecs = list(reversed(sorted(recDic.items(), key=operator.itemgetter(1))))
            sortedLists = []
            for rec in sortedRecs:
                sortedLists.append(list(rec))
            return str(sortedLists)
            return json.dumps(dict(sortedRecs))

        heroList = request.args['heroes'].split(',')
        return getRecs(heroList)
    else:
        return 'Send at least one hero.'

#port = app.config['PORT']
#manager = Manager(app)
#server = Server(host="0.0.0.0", port=port)
#manager.add_command("runserver", server)
#app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    PORT = int(os.getenv('PORT', '5050'))
    HOST = str(os.getenv('VCAP_APP_HOST', '0.0.0.0'))
    app.run(host=HOST, port=PORT,threaded=False)
    #app.run(host=HOST, port=PORT)
    #app.run()

    #manager.run()
