/**
 * Password strength scoring aligned with Django validators (min length 8).
 */
(function (global) {
    'use strict';

    const LABELS = ['', 'Weak', 'Fair', 'Strong', 'Very strong'];
    const CLASSES = ['', 'strength-weak', 'strength-fair', 'strength-strong', 'strength-very-strong'];

    function scorePassword(password) {
        if (!password) return 0;

        let score = 0;
        if (password.length >= 8) score += 1;
        if (password.length >= 12) score += 1;

        const hasLower = /[a-z]/.test(password);
        const hasUpper = /[A-Z]/.test(password);
        const hasDigit = /\d/.test(password);
        const hasSymbol = /[^A-Za-z0-9]/.test(password);

        const variety = [hasLower, hasUpper, hasDigit, hasSymbol].filter(Boolean).length;
        if (variety >= 2) score += 1;
        if (variety >= 3 && password.length >= 10) score += 1;

        return Math.min(score, 4);
    }

    function meetsMinimum(password) {
        return scorePassword(password) >= 2;
    }

    function bindStrengthMeter(inputEl, barEl, labelEl, hintEl) {
        if (!inputEl || !barEl || !labelEl) return;

        let debounceTimer;
        inputEl.addEventListener('input', function () {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function () {
                const pwd = inputEl.value;
                const score = scorePassword(pwd);

                barEl.className = 'password-strength-bar';
                labelEl.className = 'password-strength-label';

                if (!pwd) {
                    barEl.style.width = '0%';
                    labelEl.textContent = '';
                    if (hintEl) hintEl.textContent = 'Use 8+ characters with letters, numbers, and symbols.';
                    return;
                }

                const pct = (score / 4) * 100;
                barEl.style.width = pct + '%';
                if (score > 0) {
                    barEl.classList.add(CLASSES[score]);
                    labelEl.classList.add(CLASSES[score]);
                    labelEl.textContent = LABELS[score];
                }

                if (hintEl) {
                    if (score < 2) {
                        hintEl.textContent = 'Add length and mix letters, numbers, or symbols to reach Fair.';
                    } else {
                        hintEl.textContent = 'Password meets minimum strength.';
                    }
                }
            }, 120);
        });
    }

    global.PwaniNetPasswordStrength = {
        scorePassword: scorePassword,
        meetsMinimum: meetsMinimum,
        bindStrengthMeter: bindStrengthMeter,
        LABELS: LABELS,
    };
})(window);
