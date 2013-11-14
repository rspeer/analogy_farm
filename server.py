from bottle import Bottle, abort, static_file, redirect, response
import hashlib
import time
import json
import os
import sqlite3

# This was designed for several teams on one server... but there is a server for
# each team. Having a single 'your team' is the quickest hack.
teams = ['your team']
team_hashes = {'a': 'your team'}

ANSWERS = json.load(open(os.path.join(os.path.dirname(__file__), 'boxes.json')))
SPECIAL_BOXES = [0, 168, 178]
FREEBIES = ['sun', 'jupiter', 'charon']

LINKED = {
    'strike': 'c', 'c': 'strike',
    'spare': 'baby', 'baby': 'spare',
    'r': 'hotairballoon', 'hotairballoon': 'r',
    'concrete': 'sabbath', 'sabbath': 'concrete',
    'sepal': 'amphetamine', 'amphetamine': 'sepal',
    'bureau': 'bono', 'bono': 'bureau',
    'edge': 'ego', 'ego': 'edge',
    'elite': 'show', 'show': 'elite',
    'deform': 'need', 'need': 'deform',
    'hijack': 'rotary', 'rotary': 'hijack',
    'jail': 'fedora', 'fedora': 'jail',
    'middleeastern': 'hindi', 'hindi': 'middleeastern',
    'mario': 'chromium', 'chromium': 'mario',
    'card': 'define', 'define': 'card',
    'gore': 'fog', 'fog': 'gore',
    'galore': 'hotair', 'hotair': 'galore',
    'corollary': 'algorithm', 'algorithm': 'corollary',
    'arachne': 'can', 'can': 'arachne',
    'babyboom': 'majoritydecision', 'majoritydecision': 'babyboom',
    'cherenkovradiation': 'technical', 'technical': 'cherenkovradiation',
    'pace': 'roundabout', 'roundabout': 'pace',
    'show': 'elite', 'elite': 'show',
    'mint': 'dark', 'dark': 'mint',
    'jaguar': 'hack', 'hack': 'jaguar',
    'nintendo': 'titan', 'titan': 'nintendo',
    'masterwork': 'check', 'check': 'masterwork',
}

WORKING_DIR = os.path.dirname(__file__) or '.'

def connect():
    return sqlite3.connect(WORKING_DIR + '/analogy_farm.sqlite')

def create_tables():
    conn = connect()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS seen (teamhash STRING(50), box INTEGER, word STRING(50))')
    c.execute('CREATE TABLE IF NOT EXISTS guess_times (teamhash STRING(50), time REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS timeouts (teamhash STRING(50), timeout REAL)')
    conn.commit()
    conn.close()

def get_seen(teamhash,conn):
    c = conn.cursor()
    c.execute('SELECT box, word FROM seen WHERE teamhash = ?',(teamhash,))
    seen = c.fetchall()
    for word in FREEBIES:
        seen.append((ANSWERS.index(word),word))
    return seen

def get_guess_times(teamhash,conn):
    c = conn.cursor()
    now = time.time()
    c.execute('SELECT time FROM guess_times WHERE teamhash = ? AND time > ?',(teamhash,now-60))
    return [t for t, in c.fetchall()]

def get_timeout(teamhash,conn):
    c = conn.cursor()
    c.execute('SELECT timeout FROM timeouts WHERE teamhash = ? ORDER BY timeout DESC LIMIT 1',(teamhash,))
    t = c.fetchone()
    if t:
        return t[0]
    else:
        return 0.

def log_correct(teamhash,boxes):
    conn = connect()
    c = conn.cursor()
    c.executemany('INSERT INTO seen VALUES (?,?,?)',[(teamhash,box,word) for box, word in boxes]) 
    conn.commit()
    conn.close()

def log_incorrect(teamhash,timestamp):
    conn = connect()
    c = conn.cursor()
    c.execute('INSERT INTO guess_times VALUES (?,?)',(teamhash,timestamp))
    conn.commit()
    conn.close()

def log_timeout(teamhash,timeout):
    conn = connect()
    c = conn.cursor()
    c.execute('INSERT INTO timeouts VALUES (?,?)',(teamhash,timeout))
    conn.commit()
    conn.close()

def reset_db(teamhash):
    conn = connect()
    c = conn.cursor()
    c.execute('DELETE FROM seen WHERE teamhash = ?',(teamhash,))
    c.execute('DELETE FROM guess_times WHERE teamhash = ?',(teamhash,))
    c.execute('DELETE FROM timeouts WHERE teamhash = ?', (teamhash,))
    conn.commit()
    conn.close()

def normalize(word):
    word = word.replace(' ', '').lower()
    if word.endswith('shes') or word.endswith('ches') or word.endswith('xes'):
        return word[:-2]
    elif word.endswith('s'):
        return word[:-1]
    else:
        return word

def sha1(string):
    return hashlib.sha1(string).hexdigest()

class TeamInfo(object):
    def __init__(self, name, teamhash):
        self.name = name
        self.teamhash = teamhash
        self.load_data()

    def load_data(self):
        conn = connect()
        self.seen = get_seen(self.teamhash,conn)
        self.special = [box for box, word in self.seen if box in SPECIAL_BOXES]
        self.guess_times = get_guess_times(self.teamhash,conn)
        self.mintime = get_timeout(self.teamhash,conn)
        conn.close()

    def __repr__(self):
        return '<Team: %s>' % self.name

    def guess(self, box, word):
        print 'guess for %s' % self.name
        print 'seen:', self.seen
        if box >= 0 and box < len(ANSWERS) and normalize(ANSWERS[box]) == word:
            return self.guess_correct(box, word)
        else:
            return self.guess_incorrect()

    def guess_correct(self, box, word):
        """
        Called when a team has correctly guessed a word.
        """
        if (box, word) in self.seen:
            return True, []
        else:
            found = self.find_word(word)
            log_correct(self.teamhash,found)
            for box, word in found:
                self.seen.append((box, word))
                if box in SPECIAL_BOXES:
                    self.special.append(box)
            return True, found

    def guess_incorrect(self):
        now = time.time()

        # remove penalties older than a minute
        self.guess_times = [t for t in self.guess_times if t > (now - 60)]
        self.guess_times.append(now)
        log_incorrect(self.teamhash,now)

        GUESS_LIMIT = 30
        if len(self.guess_times) > GUESS_LIMIT:
            penalty = 10 * (len(self.guess_times) - GUESS_LIMIT)
            self.mintime = now + penalty
            log_timeout(self.teamhash,self.mintime)

        return False, []

    def find_word(self, word):
        results = []
        for index, bword in enumerate(ANSWERS):
            if normalize(bword) == word or normalize(bword) == LINKED.get(word):
                results.append((index, bword))
        return results

application = Bottle()

@application.route('/analogy/<teamhash>/<box>/<guess>')
def receive_guess(teamhash, box, guess):
    if guess == 'grey':
        guess = 'gray'

    if teamhash not in team_hashes:
        abort(401)

    try:
        box = int(box)
    except ValueError:
        abort(404)

    teaminfo = TeamInfo(team_hashes[teamhash],teamhash)
    if time.time() < teaminfo.mintime:
        output = {
            'error': 'guessing too fast',
            'timeout': teaminfo.mintime
        }
        response.status = 429
        return output

    correct, new_words = teaminfo.guess(box, guess)
#    time.sleep(0.5) # uncomment to simulate a laggy server

    output = {
        'correct': correct,
        'new_words': new_words,
        'all_words': teaminfo.seen,
        'special': teaminfo.special,
        'timeout': teaminfo.mintime
    }
    return json.dumps(output)

@application.route('/reset/<teamhash>')
def reset(teamhash):
    if teamhash not in team_hashes:
        abort(401)

    reset_db(teamhash)
    return 'OK'

@application.route('/analogy/<teamhash>')
def status(teamhash):
    if teamhash not in team_hashes:
        abort(401)

    teaminfo = TeamInfo(team_hashes[teamhash],teamhash)
    output = {
        'all_words': teaminfo.seen,
        'special': teaminfo.special,
        'timeout': teaminfo.mintime
    }
    return json.dumps(output)

@application.route('/static/<teamhash>/<path:path>')
def index(teamhash, path):
    if teamhash not in team_hashes:
        abort(401)
    
    return static_file(path, root=WORKING_DIR+'/static')

# The puzzle page at www.coinheist.com links straight to /analogy_farm/
# So we'll redirect it to the right place.
@application.route('/')
def root():
    redirect('static/a/index.html')

create_tables()
# Disabled: hack to get to one-team-per-server
#for i, team in enumerate(teams):
#    salted = 'batmanalogyroscope_' + team
#    teamhash = sha1(salted)
#    team_hashes[teamhash] = team
#    print team, '\t', teamhash

if __name__ == '__main__':
    application.run(host='0.0.0.0', port=10000)
