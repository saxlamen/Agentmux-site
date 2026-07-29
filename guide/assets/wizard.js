(function () {
    'use strict';

    var root = document.getElementById('wizard');
    if (!root) return;
    var lang = root.getAttribute('data-lang');
    var data = null;
    var strings = null;
    var answers = {};

    function get(url) {
        return fetch(url).then(function (r) {
            if (!r.ok) throw new Error(url);
            return r.json();
        });
    }

    function readHash() {
        var raw = location.hash.replace(/^#/, '');
        if (!raw) return {};
        var parts = raw.split('.');
        var out = {};
        for (var i = 0; i < data.questions.length && i < parts.length; i++) {
            var q = data.questions[i];
            if (q.options.indexOf(parts[i]) !== -1) out[q.id] = parts[i];
        }
        return out;
    }

    function writeHash() {
        var parts = data.questions.map(function (q) { return answers[q.id] || ''; });
        while (parts.length && !parts[parts.length - 1]) parts.pop();
        history.replaceState({}, '', parts.length ? '#' + parts.join('.') : location.pathname);
    }

    function complete() {
        return data.questions.every(function (q) { return answers[q.id]; });
    }

    function applies(step) {
        var when = step.when || {};
        return Object.keys(when).every(function (k) {
            return when[k].indexOf(answers[k]) !== -1;
        });
    }

    function el(tag, cls, text) {
        var n = document.createElement(tag);
        if (cls) n.className = cls;
        if (text) n.textContent = text;
        return n;
    }

    function copyText(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            return navigator.clipboard.writeText(text);
        }
        // Non-HTTPS origins expose no async clipboard API. The legacy
        // textarea + execCommand path still works there.
        return new Promise(function (resolve, reject) {
            var ta = document.createElement('textarea');
            ta.value = text;
            ta.setAttribute('readonly', '');
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            var ok = false;
            try {
                ok = document.execCommand('copy');
            } catch (e) {
                ok = false;
            }
            document.body.removeChild(ta);
            if (ok) { resolve(); } else { reject(new Error('copy unavailable')); }
        });
    }

    function renderQuestions() {
        root.innerHTML = '';
        data.questions.forEach(function (q) {
            var qs = strings.ui.questions[q.id];
            var box = el('fieldset', 'wizard-question');
            box.appendChild(el('legend', null, qs.label));
            q.options.forEach(function (opt) {
                var btn = el('button', 'wizard-option', qs.options[opt]);
                btn.type = 'button';
                var selected = answers[q.id] === opt;
                if (selected) btn.classList.add('is-selected');
                btn.setAttribute('aria-pressed', selected ? 'true' : 'false');
                btn.addEventListener('click', function () {
                    answers[q.id] = opt;
                    writeHash();
                    render();
                });
                box.appendChild(btn);
            });
            root.appendChild(box);
        });
    }

    function renderStep(step, index) {
        var s = strings.steps[step.id];
        var card = el('li', 'wizard-step');
        card.appendChild(el('h3', 'wizard-step-title', index + '. ' + s.title));

        var why = el('p', 'wizard-why');
        why.appendChild(el('strong', null, strings.ui.why + '：'));
        why.appendChild(document.createTextNode(' ' + s.why));
        card.appendChild(why);

        (step.commands || []).forEach(function (cmd) {
            var row = el('div', 'wizard-cmd');
            var pre = el('pre');
            pre.appendChild(el('code', null, cmd));
            row.appendChild(pre);
            var copy = el('button', 'wizard-copy', strings.ui.copy);
            copy.type = 'button';
            copy.addEventListener('click', function () {
                copyText(cmd).then(function () {
                    copy.textContent = strings.ui.copied;
                    setTimeout(function () { copy.textContent = strings.ui.copy; }, 1500);
                }).catch(function () {
                    copy.textContent = strings.ui.copyFailed;
                    setTimeout(function () { copy.textContent = strings.ui.copy; }, 1500);
                });
            });
            row.appendChild(copy);
            card.appendChild(row);
        });

        var verify = el('p', 'wizard-verify');
        verify.appendChild(el('strong', null, strings.ui.verify + '：'));
        verify.appendChild(document.createTextNode(' ' + s.verifyHint));
        if (step.verify) {
            var v = el('pre');
            v.appendChild(el('code', null, step.verify));
            card.appendChild(verify);
            card.appendChild(v);
        } else {
            card.appendChild(verify);
        }

        var fail = el('p', 'wizard-fail');
        fail.appendChild(el('strong', null, strings.ui.fail + '：'));
        fail.appendChild(document.createTextNode(' ' + s.failHint + ' '));
        if (step.troubleshoot) {
            var link = el('a', null, '→');
            link.href = '/guide/' + lang + '/troubleshooting/#' + step.troubleshoot;
            fail.appendChild(link);
        }
        card.appendChild(fail);
        return card;
    }

    function renderPlan() {
        root.innerHTML = '';
        var list = el('ol', 'wizard-plan');
        var n = 0;
        data.steps.filter(applies).forEach(function (step) {
            n += 1;
            list.appendChild(renderStep(step, n));
        });
        root.appendChild(list);

        var actions = el('div', 'wizard-actions');
        var again = el('button', 'wizard-restart', strings.ui.restart);
        again.type = 'button';
        again.addEventListener('click', function () {
            answers = {};
            writeHash();
            render();
        });
        actions.appendChild(again);

        var share = el('button', 'wizard-share', strings.ui.share);
        share.type = 'button';
        share.addEventListener('click', function () {
            copyText(location.href).then(function () {
                share.textContent = strings.ui.copied;
                setTimeout(function () { share.textContent = strings.ui.share; }, 1500);
            }).catch(function () {
                share.textContent = strings.ui.copyFailed;
                setTimeout(function () { share.textContent = strings.ui.share; }, 1500);
            });
        });
        actions.appendChild(share);
        root.appendChild(actions);
    }

    function render() {
        if (complete()) renderPlan(); else renderQuestions();
    }

    Promise.all([
        get('/guide/assets/steps.json'),
        get('/guide/assets/wizard-' + lang + '.json')
    ]).then(function (res) {
        data = res[0];
        strings = res[1];
        answers = readHash();
        render();
    }).catch(function () {
        root.textContent = '載入失敗，請重新整理。';
    });
})();
