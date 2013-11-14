var SERVER = window.location.href.split('/')[2];
/* change this when you change how you're hosting it! */
var SERVER_URL = "http://" + SERVER + "/analogy/";
var TEAM_KEY = 'a';

var words = {};
var boxes = {};

var last_guess_time = (new Date()).getTime()/1000;

function add(box, word) {
    words[box] = word;
    boxes[box].attr('disabled', true).val(word);
}

function special(box) {
    boxes[box].addClass('special');
}

function process(data, guessed_box) {
    if (data.correct === true) {
        TransientMessage.showMessage("Correct");
    }
    else if (data.correct === false) {
        TransientMessage.showMessage("Incorrect");
        boxes[guessed_box].val('');
    }
    data.all_words.forEach(function (item) {
        var box = item[0];
        var word = item[1];
        add(box, word);
    });
    data.special.forEach(special);
}

function query(box, guess) {
    var url = SERVER_URL + TEAM_KEY;
    if (box !== undefined && guess !== undefined) {
        url += '/' + box + '/' + encodeURIComponent(guess);
    }
    console.log(url);
    $.ajax(url, {
        dataType: 'json',
        statusCode: {
            200: function (data) {
                console.log(data);
                process(data, box);
            },
            429: function (error) {
                var data = JSON.parse(error.responseText);
                console.log(data);
                var now = (new Date()).getTime()/1000;
                var seconds = Math.ceil(data.timeout - now);
                $(function () {
                    $(':focus').blur();
                    var dialog = Dialog.showDialog(Dialog, {
                        closeOnInsideClick: true,
                    });
                    var update = function (n) {
                        if (n <= 0) {
                            dialog.close();
                        }
                        else {
                            dialog.content("Error: guessing too fast. Try again in " + n + " seconds.<br />(click to close)");
                            setTimeout(function () {
                                update(n-1);
                            }, 1000);
                        }
                    };
                    update(seconds);
                });
            }
        }
    });
}

function normalize(word) {
    word = word.replace(' ', '');
    if (word.slice(-4) === 'ches' || word.slice(-4) === 'shes' || word.slice(-3) === 'xes') {
        word = word.slice(0, -2);
    }
    else if (word.length > 1 && word.slice(-1) === 's') {
        word = word.slice(0, -1);
    }
    return word.toLowerCase();
}

function textbox(x, y, id) {
    var elem = $('<input type="text">');
    elem.attr('id', id);
    elem.css({'position': 'absolute',
              'left': x-56,
              'top': y-17});
    elem.keydown(function (event) {
        if (event.which === 13 && elem.val() !== '') {
            var guess = normalize(elem.val());
            if (guess !== '') {
                query(id, guess);
                last_guess_time = (new Date()).getTime()/1000;
            }
//          this.value = '';
        }
    });
    boxes[id] = elem;
    return elem;
}

$(function () {
    query();
    setInterval(function () {
        now = (new Date()).getTime()/1000;
        if (now - last_guess_time < 600) {
            query();
        }
    }, 10000);
});
