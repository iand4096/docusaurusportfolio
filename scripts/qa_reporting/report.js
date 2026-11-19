    const severityFilter = document.getElementById('severityFilter');
    const sourceFilter = document.getElementById('sourceFilter');
    const feedbackFilter = document.getElementById('feedbackFilter');
    const latestReportLink = document.getElementById('latestReportLink');
    if (latestReportLink) {
        latestReportLink.addEventListener('click', (event) => {
            event.preventDefault();
            const url = new URL(window.location.href);
            url.searchParams.set('_qa_refresh', Date.now().toString());
            window.location.assign(url.toString());
        });
    }
    function applyFilters() {
        const severity = severityFilter.value;
        const source = sourceFilter.value;
        const recurrence = feedbackFilter.value;
        document.querySelectorAll('[data-source-filter]').forEach(button => {
            button.setAttribute('aria-pressed', String(button.dataset.sourceFilter === source));
        });
        const rows = document.querySelectorAll('tr[data-severity]');
        let shown = 0;
        for (const row of rows) {
            const matches = (!severity || row.dataset.severity === severity) &&
                (!source || row.dataset.source === source) &&
                (!recurrence || (recurrence === 'ai-clear' ? row.dataset.aiClear === 'true' :
                    row.dataset.recurrence === recurrence));
            row.style.display = matches ? '' : 'none';
            if (matches) shown++;
        }
        document.getElementById('findingFilterStatus').textContent = shown + ' of ' + rows.length +
            ' findings shown' + (shown === 0 ? '. No findings match these filters.' : '.');
    }
    severityFilter.addEventListener('change', applyFilters);
    sourceFilter.addEventListener('change', applyFilters);
    document.querySelectorAll('[data-source-filter]').forEach(button => {
        button.addEventListener('click', () => {
            sourceFilter.value = button.dataset.sourceFilter;
            // The AI-only view must not mask deterministic source findings.
            if (feedbackFilter.value === 'ai-clear' && sourceFilter.value !== 'ai') {
                feedbackFilter.value = '';
            }
            applyFilters();
        });
    });
    feedbackFilter.addEventListener('change', () => {
        if (feedbackFilter.value === 'ai-clear') sourceFilter.value = 'ai';
        applyFilters();
    });
    function showLinkView(value) {
        severityFilter.value = '';
        sourceFilter.value = '';
        feedbackFilter.value = value;
        applyFilters();
    }
    const showAIWithoutRecurrence = document.getElementById('showAIWithoutRecurrence');
    if (showAIWithoutRecurrence) showAIWithoutRecurrence.addEventListener('click', () => {
        showLinkView('ai-clear');
        sourceFilter.value = 'ai';
        applyFilters();
        document.getElementById('activeFindingsTitle').scrollIntoView();
    });
    const showPossibleLinks = document.getElementById('showPossibleLinks');
    if (showPossibleLinks) showPossibleLinks.addEventListener('click', () => {
        showLinkView('possible');
        document.getElementById('activeFindingsTitle').scrollIntoView();
    });
    const showAllFindings = document.getElementById('showAllFindings');
    if (showAllFindings) showAllFindings.addEventListener('click', () => showLinkView(''));
    document.querySelectorAll('.review-recurrence').forEach(link => {
        link.addEventListener('click', () => {
            showLinkView('');
            const row = document.getElementById(link.getAttribute('href').slice(1));
            const details = row.querySelector('.recurrence-details');
            if (details) details.open = true;
            const history = row.closest('.feedback-history');
            if (history) history.open = true;
        });
    });
    applyFilters();

    // Keep copied recurrence commands bound to the immutable published report.
    const publishedReport = (window.location.protocol === 'https:' &&
        window.location.hostname === 'iand4096.github.io' &&
        /^\/docusaurusportfolio\/qa\/report-[a-f0-9]{12,40}\.html$/i.test(window.location.pathname))
        ? window.location.origin + window.location.pathname.replace(/\.html$/i, '.json') : null;
    if (!__PINNED_REPORT_JSON__ && publishedReport) {
        document.querySelectorAll('.link-command').forEach(code => {
            code.textContent = code.textContent.replace(code.dataset.reportToken, JSON.stringify(publishedReport));
        });
    }
    document.querySelectorAll('.copy-link-command').forEach(button => {
        button.addEventListener('click', async () => {
            const command = button.previousElementSibling.querySelector('code').textContent;
            try {
                await navigator.clipboard.writeText(command);
                document.getElementById('copyStatus').textContent = 'Command copied. Edit the reason, run locally, then render the report again.';
            } catch (error) {
                window.prompt('Copy command and edit the reason:', command);
            }
        });
    });

    // Works on static GitHub Pages without an API key or a server component.
    // Single quotes around the reason are intentional: replace its contents
    // with your own explanation, or use --reason-file for complex quotations.
    document.querySelectorAll('.challenge-button').forEach((button) => {
        button.addEventListener('click', async () => {
            const issueId = button.dataset.issueId;
            if (!/^qa-[A-Za-z0-9_-]+$/.test(issueId || '')) return;
            const reportRef = __PINNED_REPORT_JSON__ || ((window.location.protocol === 'https:' &&
                window.location.hostname === 'iand4096.github.io' &&
                /^\/docusaurusportfolio\/qa\/report-[a-f0-9]{12,40}\.html$/i.test(window.location.pathname))
                ? window.location.origin + window.location.pathname.replace(/\.html$/i, '.json')
                : __LOCAL_REPORT_JSON__);
            const command = 'python3 scripts/ai_docs_review.py challenge --report ' +
                JSON.stringify(reportRef) + ' --issue ' + issueId +
                ' --reason "Explain why you disagree with this finding"';
            const status = document.getElementById('copyStatus');
            try {
                if (!navigator.clipboard || !navigator.clipboard.writeText) {
                    throw new Error('Clipboard API unavailable');
                }
                await navigator.clipboard.writeText(command);
                status.textContent = 'Challenge command copied for ' + issueId
                    + '. Edit the reason and run it in your terminal.';
                const previous = button.textContent;
                button.textContent = 'Copied!';
                window.setTimeout(() => { button.textContent = previous; }, 1800);
            } catch (error) {
                // Non-secure origins and browsers that deny clipboard access:
                // show the complete command for manual copying instead.
                window.prompt('Copy this command and edit the reason:', command);
                status.textContent = 'Challenge command shown for ' + issueId + '.';
            }
        });
    });
