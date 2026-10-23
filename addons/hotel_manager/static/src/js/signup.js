(function () {
    'use strict';
    var form = document.getElementById('hm-signup-form');
    if (!form) { return; }

    var steps = Array.prototype.slice.call(form.querySelectorAll('.hm-step'));
    var dots = Array.prototype.slice.call(document.querySelectorAll('.hm-progress li'));
    var fill = document.querySelector('.hm-bar-fill');
    var current = 0;

    function show(index) {
        current = index;
        steps.forEach(function (s, i) { s.classList.toggle('is-active', i === index); });
        dots.forEach(function (d, i) {
            d.classList.toggle('is-active', i === index);
            d.classList.toggle('is-done', i < index);
        });
        if (fill) { fill.style.width = ((index + 1) / steps.length * 100) + '%'; }
        var first = steps[index].querySelector('input:not([type=radio])');
        if (first) { first.focus(); }
    }

    function stepIsValid(index) {
        var inputs = steps[index].querySelectorAll('input');
        for (var i = 0; i < inputs.length; i++) {
            if (!inputs[i].checkValidity()) {
                inputs[i].reportValidity();
                return false;
            }
        }
        return true;
    }

    form.addEventListener('click', function (ev) {
        var next = ev.target.closest('[data-next]');
        var back = ev.target.closest('[data-back]');
        if (next && stepIsValid(current)) { show(Math.min(current + 1, steps.length - 1)); }
        if (back) { show(Math.max(current - 1, 0)); }
    });

    form.addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter' && current < steps.length - 1 && ev.target.tagName === 'INPUT') {
            ev.preventDefault();
            if (stepIsValid(current)) { show(current + 1); }
        }
    });

    var options = form.querySelectorAll('.hm-plan-opt');
    form.addEventListener('change', function (ev) {
        if (ev.target.name !== 'plan_code') { return; }
        Array.prototype.forEach.call(options, function (o) {
            o.classList.toggle('is-selected', o.contains(ev.target));
        });
    });

    form.addEventListener('submit', function () {
        var btn = form.querySelector('[type=submit]');
        if (btn) { btn.disabled = true; btn.textContent = 'Creating your hotel...'; }
    });

    show(document.querySelector('.hm-error') ? 1 : 0);
}());
