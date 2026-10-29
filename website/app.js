/* ==========================================================================
   IPL INSIGHTX • CORE APPLICATION LOGIC & VISUALIZATION ENGINE
   Features: Official IPL Color Palette (Royal Blue #19398A & Sky Blue #5091CD),
   Day/Night Stadium Theme Engine, Animated Number Counters, Rich Emojis,
   Dynamic Scroll Progress & Interactive Analytics
   ========================================================================== */

let DATA = null, view = 'overview', season = 'all';

// DOM & Formatting Utilities
const $ = s => document.querySelector(s);
const num = v => Number(v || 0).toLocaleString('en-IN');
const pct = (n, d) => d ? (100 * n / d).toFixed(1) + '%' : '—';
const escapeHtml = v => String(v).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// Exact Colors from Official IPL Logo
const iplRoyal = '#19398A';
const iplRoyalDark = '#0E2766';
const iplSky = '#5091CD';
const iplSkyLight = '#70A9DE';
const iplSlate = '#64748B';

// Function to generate Plotly layout matching current theme
function getPlotlyLayout() {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  return {
    paper_bgcolor: 'rgba(0, 0, 0, 0)',
    plot_bgcolor: 'rgba(0, 0, 0, 0)',
    font: { family: 'Plus Jakarta Sans, Outfit, sans-serif', color: isDark ? '#E2E8F0' : '#334155', size: 11.5 },
    margin: { l: 52, r: 24, t: 30, b: 50 },
    showlegend: false,
    xaxis: {
      gridcolor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(25, 57, 138, 0.08)',
      zerolinecolor: isDark ? 'rgba(255, 255, 255, 0.12)' : 'rgba(25, 57, 138, 0.15)',
      tickfont: { color: isDark ? '#94A3B8' : '#64748B', size: 10.5, family: 'Outfit, sans-serif' }
    },
    yaxis: {
      gridcolor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(25, 57, 138, 0.08)',
      zerolinecolor: isDark ? 'rgba(255, 255, 255, 0.12)' : 'rgba(25, 57, 138, 0.15)',
      tickfont: { color: isDark ? '#94A3B8' : '#64748B', size: 10.5, family: 'Outfit, sans-serif' }
    },
    hoverlabel: {
      bgcolor: iplRoyal,
      bordercolor: iplSky,
      font: { family: 'Outfit, sans-serif', color: '#FFFFFF', size: 12 }
    }
  };
}

const filter = a => a.filter(x => season === 'all' || String(x.season) === season);
const sum = (a, k) => a.reduce((n, x) => n + Number(x[k] || 0), 0);

// Emoji mapping for metric categories
const metricEmojis = {
  'Matches': '🏟️',
  'Delivery events': '⚡',
  'Total runs': '🏏',
  'Sixes': '💥',
  'Batters': '🧢',
  'Runs': '🏏',
  'Fours': '⚡',
  'Qualified bowlers': '🎯',
  'Bowler wickets': '🎯',
  'Legal deliveries': '⚾',
  'Runs conceded': '🔴',
  'Wins': '🏆',
  'Win rate': '📈',
  'Toss wins': '🪙',
  'First innings': '⏱️',
  'Average first innings': '📊',
  'Venue seasons': '📅',
  'Head-to-head': '⚔️',
  'Source matches': '📁',
  'Data engine': '⚙️',
  'Storage': '💾'
};

// Metric Cards with animated count-up and emojis
function cards(a) {
  return `<div class="metrics">${a.map(([k, v, f]) => {
    const rawMatch = String(v).replace(/,/g, '');
    const isNum = !isNaN(rawMatch) && rawMatch.trim() !== '';
    const isPercent = String(v).endsWith('%');
    const numericVal = isPercent ? parseFloat(v) : (isNum ? Number(rawMatch) : null);
    const emoji = metricEmojis[k] || (k.includes('wins') ? '🏆' : '📊');

    return `
      <div class="metric scroll-reveal">
        <div class="k"><span aria-hidden="true">${emoji}</span> ${k}</div>
        <div class="v" ${numericVal !== null ? `data-target="${numericVal}" data-is-pct="${isPercent}"` : ''}>${v}</div>
        <div class="f">${f || '⚡ Official IPL Historical Data'}</div>
      </div>
    `;
  }).join('')}</div>`;
}

// Panel container with headers
function panel(name, id, subtitle = '') {
  return `
    <div class="panel scroll-reveal">
      <h3>${name}</h3>
      ${subtitle ? `<p>${subtitle}</p>` : ''}
      <div id="${id}" class="chart"></div>
    </div>
  `;
}

// Table generation with interactive download and expand
function tableRows(arr, cols) {
  return arr.map(x => `
    <tr>${cols.map(([k]) => `<td>${escapeHtml(x[k] ?? '—')}</td>`).join('')}</tr>
  `).join('');
}

function table(arr, cols, id) {
  let shown = arr.slice(0, 100);
  let hasMore = arr.length > 100;
  let s = `
    <div class="panel scroll-reveal">
      <div class="tablewrap">
        <table class="data-table">
          <thead>
            <tr>${cols.map(c => `<th>${c[1]}</th>`).join('')}</tr>
          </thead>
          <tbody id="${id}Rows">${tableRows(shown, cols)}</tbody>
        </table>
      </div>
      <div class="table-actions">
        <p id="${id}Count" class="table-count">
          📊 ${hasMore ? `Showing first 100 of ${num(arr.length)} records` : `${num(arr.length)} records`}
        </p>
        <div class="table-buttons">
          ${hasMore ? `<button class="btn btn-secondary" id="${id}ShowAll" aria-expanded="false">👁️ Show all ${num(arr.length)}</button>` : ''}
          <button class="btn" id="${id}">📥 Download CSV</button>
        </div>
      </div>
    </div>
  `;

  setTimeout(() => {
    let btn = $('#' + id);
    if (btn) btn.onclick = () => downloadCSV(arr, cols.map(x => x[0]));
    let showAll = $('#' + id + 'ShowAll');
    if (showAll) {
      showAll.onclick = () => {
        let expanded = showAll.getAttribute('aria-expanded') === 'true';
        $('#' + id + 'Rows').innerHTML = tableRows(expanded ? shown : arr, cols);
        showAll.setAttribute('aria-expanded', String(!expanded));
        showAll.innerHTML = expanded ? `👁️ Show all ${num(arr.length)}` : `⚡ Show first 100`;
        $('#' + id + 'Count').innerHTML = expanded ? `📊 Showing first 100 of ${num(arr.length)} records` : `📊 Showing all ${num(arr.length)} records`;
      };
    }
  }, 0);

  return s;
}

function downloadCSV(a, cols) {
  let lines = [
    cols.join(','),
    ...a.map(x => cols.map(k => '"' + String(x[k] ?? '').replace(/"/g, '""') + '"').join(','))
  ];
  let url = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/csv' }));
  let aEl = document.createElement('a');
  aEl.href = url;
  aEl.download = 'ipl-insightx-' + view + '.csv';
  aEl.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// Chart Renderers using Official IPL Colors
function line(id, x, y, title = '', color = iplSky) {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  Plotly.react(id, [{
    x, y,
    type: 'scatter',
    mode: 'lines+markers',
    line: { color: iplSky, width: 3.5, shape: 'spline' },
    marker: { size: 8, color: iplRoyal, line: { color: '#FFFFFF', width: 2 } },
    fill: 'tozeroy',
    fillcolor: isDark ? 'rgba(80, 145, 205, 0.12)' : 'rgba(80, 145, 205, 0.1)',
    hovertemplate: '<b>Season %{x}</b><br>Count: %{y:,}<extra></extra>'
  }], {
    ...getPlotlyLayout(),
    title: title ? { text: title, font: { family: 'Outfit, sans-serif', size: 14, color: isDark ? '#FFFFFF' : iplRoyal } } : undefined
  }, { responsive: true, displaylogo: false });
}

function bar(id, labels, values, horizontal = false, customColor = null) {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const defaultBar = horizontal ? iplRoyal : iplSky;
  const barColor = customColor || defaultBar;

  Plotly.react(id, [{
    type: 'bar',
    x: horizontal ? values : labels,
    y: horizontal ? labels : values,
    orientation: horizontal ? 'h' : 'v',
    marker: {
      color: barColor,
      line: { color: horizontal ? iplSky : iplRoyal, width: 1.2 },
      opacity: 0.95
    },
    hovertemplate: horizontal ? '<b>%{y}</b><br>%{x:,}<extra></extra>' : '<b>%{x}</b><br>%{y:,}<extra></extra>'
  }], {
    ...getPlotlyLayout(),
    margin: horizontal ? { l: 155, r: 24, t: 20, b: 45 } : getPlotlyLayout().margin
  }, { responsive: true, displaylogo: false });
}

function pie(id, labels, values) {
  Plotly.react(id, [{
    type: 'pie',
    labels,
    values,
    hole: 0.66,
    marker: {
      colors: [iplRoyal, iplSky, iplSlate, '#3B82C4', '#94A3B8'],
      line: { color: '#FFFFFF', width: 2.5 }
    },
    textinfo: 'percent+label',
    textfont: { family: 'Outfit, sans-serif', size: 11.5, color: '#FFFFFF' },
    hoverinfo: 'label+value+percent'
  }], {
    ...getPlotlyLayout(),
    showlegend: false
  }, { responsive: true, displaylogo: false });
}

// Section Headings & Subtitles with Emojis
function headings() {
  const cfg = {
    overview: ['⚡ Cricket, Decoded.', 'An executive analytics command center to explore the numbers behind every IPL season.'],
    teams: ['🛡️ Franchise Intelligence', 'Deep-dive match records, toss advantages, and historic win trajectories.'],
    batting: ['🏏 Batting Studio', 'Strike rates, boundary frequencies, and historic run-making aggregates.'],
    bowling: ['🎯 Bowling Studio', 'Wicket hauls, economy rates, and bowling impact analytics.'],
    venues: ['🏟️ Venue Explorer', 'Pitch behaviors, first-innings scoring distributions, and legendary grounds.'],
    headtohead: ['⚔️ The Rivalries', 'Side-by-side legacy battles between iconic IPL franchises.'],
    engineering: ['💻 Big Data Lakehouse Lab', 'Apache Spark ETL pipeline, Delta Lake architecture & distributed storage.'],
    sources: ['ℹ️ Data Sources & Limitations', 'Transparent provenance, Cricsheet ball-by-ball schemas, and specs.']
  };

  $('#heading').textContent = cfg[view][0];
  $('#subheading').textContent = cfg[view][1];
  $('#overviewHero').hidden = (view !== 'overview');
  document.querySelectorAll('.navitem').forEach(n => n.classList.toggle('active', n.dataset.view === view));
}

// Smooth Number Counter Animation
function triggerNumberCounters() {
  const elements = document.querySelectorAll('.metric .v[data-target]');
  elements.forEach(el => {
    const target = parseFloat(el.getAttribute('data-target'));
    const isPct = el.getAttribute('data-is-pct') === 'true';
    if (isNaN(target)) return;

    const duration = 750;
    const startTime = performance.now();

    function updateCounter(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      const current = progress === 1 ? target : (target * ease);

      el.textContent = isPct ? current.toFixed(1) + '%' : Math.round(current).toLocaleString('en-IN');

      if (progress < 1) {
        requestAnimationFrame(updateCounter);
      }
    }
    requestAnimationFrame(updateCounter);
  });
}

// Intersection Observer for scroll animations
function initScrollObserver() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed');
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.scroll-reveal').forEach(el => observer.observe(el));
}

// Top scroll progress bar calculator
function initScrollProgress() {
  const progressBar = $('#scrollProgress');
  if (!progressBar) return;

  window.addEventListener('scroll', () => {
    const scrollTop = window.scrollY || document.documentElement.scrollTop;
    const docHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    const scrollPercent = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
    progressBar.style.width = scrollPercent + '%';
  }, { passive: true });
}

// Main View Renderer
function render() {
  if (!DATA) return;
  headings();

  const m = filter(DATA.matches);
  const s = filter(DATA.seasons);
  const bat = filter(DATA.batting);
  const bow = filter(DATA.bowling);
  const ven = filter(DATA.venues);
  const content = $('#content');
  $('#message').textContent = '';

  if (view === 'overview') {
    content.innerHTML = cards([
      ['Matches', num(m.length)],
      ['Delivery events', num(sum(s, 'events'))],
      ['Total runs', num(sum(s, 'runs'))],
      ['Sixes', num(sum(s, 'sixes'))]
    ]) + `
      <div class="grid2">
        ${panel('🏏 Runs Through The Years', 'c1', 'Season-by-season aggregate runs scored across the IPL')}
        ${panel('💥 Six Hitting Trend', 'c2', 'Maximums that cleared the boundary ropes per edition')}
      </div>
      <div class="grid2">
        ${panel('👑 Top Run Scorers (Orange Cap)', 'c3', 'Leading batters in the selected tournament period')}
        ${panel('🏆 Most Match Wins', 'c4', 'Most successful franchises recorded by Cricsheet')}
      </div>
    `;

    const ss = [...s].sort((a, b) => String(a.season).localeCompare(String(b.season)));
    bar('c1', ss.map(x => x.season), ss.map(x => x.runs), false, iplRoyal);
    line('c2', ss.map(x => x.season), ss.map(x => x.sixes), '', iplSky);

    let b = aggregate(bat, 'batter', ['runs']).sort((a, b) => b.runs - a.runs).slice(0, 10).reverse();
    bar('c3', b.map(x => x.batter), b.map(x => x.runs), true, iplRoyal);

    let w = counts(m.filter(x => x.winner), 'winner').slice(0, 10).reverse();
    bar('c4', w.map(x => x.label), w.map(x => x.count), true, iplSky);

  } else if (view === 'teams') {
    let teams = allTeams(m);
    content.innerHTML = `
      <div class="toolbar scroll-reveal">
        <div class="field">
          <label>🛡️ SELECT FRANCHISE</label>
          <div class="select-wrapper">
            <select id="team">
              ${teams.map(x => `<option>${escapeHtml(x)}</option>`).join('')}
            </select>
            <span class="select-chevron" aria-hidden="true">▼</span>
          </div>
        </div>
      </div>
      <div id="teamInfo"></div>
    `;

    const paint = () => {
      let t = $('#team').value;
      let a = m.filter(x => x.team1 === t || x.team2 === t);
      let win = a.filter(x => x.winner === t);

      $('#teamInfo').innerHTML = cards([
        ['Matches', num(a.length)],
        ['Wins', num(win.length)],
        ['Win rate', pct(win.length, a.length)],
        ['Toss wins', num(a.filter(x => x.toss_winner === t).length)]
      ]) + `
        <div class="grid2">
          ${panel('📈 Seasonal Win %', 't1', 'Yearly win conversion rate for ' + escapeHtml(t))}
          ${panel('🪙 Toss Impact vs Match Outcome', 't2', 'Win rates when winning vs losing toss')}
        </div>
      ` + table(a, ['date', 'season', 'team1', 'team2', 'winner'].map(x => [x, x.toUpperCase()]), 'teamCsv');

      let by = aggregate(a, 'season', []).sort((a, b) => String(a.season).localeCompare(String(b.season)));
      bar('t1', by.map(x => x.season), by.map(x => 100 * a.filter(z => z.season === x.season && z.winner === t).length / x.count), false, iplRoyal);

      let yes = a.filter(x => x.toss_winner === t);
      let no = a.filter(x => x.toss_winner !== t);
      bar('t2', ['Won Toss', 'Lost Toss'], [
        yes.length ? 100 * yes.filter(x => x.winner === t).length / yes.length : 0,
        no.length ? 100 * no.filter(x => x.winner === t).length / no.length : 0
      ], false, iplSky);

      triggerNumberCounters();
      initScrollObserver();
    };

    $('#team').onchange = paint;
    paint();

  } else if (view === 'batting') {
    content.innerHTML = `
      <div class="toolbar scroll-reveal">
        <div class="field">
          <label>🏏 MINIMUM BALLS FACED</label>
          <div class="select-wrapper">
            <select id="minballs">
              <option value="0">Any ball count</option>
              <option value="100" selected>⚡ 100+ balls faced</option>
              <option value="300">🔥 300+ balls faced</option>
              <option value="600">👑 600+ balls faced</option>
            </select>
            <span class="select-chevron" aria-hidden="true">▼</span>
          </div>
        </div>
      </div>
      <div id="batInfo"></div>
    `;

    const paint = () => {
      let min = Number($('#minballs').value);
      let a = aggregate(bat, 'batter', ['runs', 'balls', 'fours', 'sixes'])
        .map(x => ({ ...x, strike_rate: x.balls ? (100 * x.runs / x.balls).toFixed(2) : '—' }))
        .filter(x => x.balls >= min)
        .sort((x, y) => y.runs - x.runs);

      $('#batInfo').innerHTML = cards([
        ['Batters', num(a.length)],
        ['Runs', num(sum(a, 'runs'))],
        ['Fours', num(sum(a, 'fours'))],
        ['Sixes', num(sum(a, 'sixes'))]
      ]) + panel('🏏 Highest Run Scorers', 'bat1', 'Top batters matching criteria')
        + table(a, [
          ['batter', 'BATTER'],
          ['runs', 'RUNS'],
          ['balls', 'BALLS'],
          ['strike_rate', 'STRIKE RATE'],
          ['fours', 'FOURS (4s)'],
          ['sixes', 'SIXES (6s)']
        ], 'batCSV');

      let top = a.slice(0, 15).reverse();
      bar('bat1', top.map(x => x.batter), top.map(x => x.runs), true, iplRoyal);

      triggerNumberCounters();
      initScrollObserver();
    };

    $('#minballs').onchange = paint;
    paint();

  } else if (view === 'bowling') {
    content.innerHTML = `
      <div class="toolbar scroll-reveal">
        <div class="field">
          <label>🎯 MINIMUM LEGAL DELIVERIES</label>
          <div class="select-wrapper">
            <select id="minbowls">
              <option value="0">Any deliveries</option>
              <option value="120" selected>⚡ 120+ legal balls</option>
              <option value="300">🔥 300+ legal balls</option>
              <option value="600">👑 600+ legal balls</option>
            </select>
            <span class="select-chevron" aria-hidden="true">▼</span>
          </div>
        </div>
      </div>
      <div id="bowlInfo"></div>
    `;

    const paint = () => {
      let min = Number($('#minbowls').value);
      let a = aggregate(bow, 'bowler', ['wickets', 'runs', 'balls'])
        .map(x => ({ ...x, economy: x.balls ? (x.runs * 6 / x.balls).toFixed(2) : '—' }))
        .filter(x => x.balls >= min)
        .sort((a, b) => b.wickets - a.wickets);

      $('#bowlInfo').innerHTML = cards([
        ['Qualified bowlers', num(a.length)],
        ['Bowler wickets', num(sum(a, 'wickets'))],
        ['Legal deliveries', num(sum(a, 'balls'))],
        ['Runs conceded', num(sum(a, 'runs'))]
      ]) + panel('🎯 Purple Cap Contenders (Wicket Leaders)', 'bo1', 'Bowlers with most wickets')
        + table(a, [
          ['bowler', 'BOWLER'],
          ['wickets', 'WICKETS'],
          ['economy', 'ECONOMY'],
          ['balls', 'LEGAL BALLS']
        ], 'bowlCSV');

      let top = a.slice(0, 15).reverse();
      bar('bo1', top.map(x => x.bowler), top.map(x => x.wickets), true, iplRoyal);

      triggerNumberCounters();
      initScrollObserver();
    };

    $('#minbowls').onchange = paint;
    paint();

  } else if (view === 'venues') {
    let v = aggregate(ven, 'venue', ['total', 'innings']).filter(x => x.innings >= 5).sort((a, b) => b.innings - a.innings);
    content.innerHTML = `
      <div class="toolbar scroll-reveal">
        <div class="field">
          <label>🏟️ SELECT CRICKET GROUND</label>
          <div class="select-wrapper">
            <select id="venue">
              ${v.map(x => `<option>${escapeHtml(x.venue)}</option>`).join('')}
            </select>
            <span class="select-chevron" aria-hidden="true">▼</span>
          </div>
        </div>
      </div>
      <div id="venueInfo"></div>
    `;

    const paint = () => {
      let vv = $('#venue').value;
      let rows = ven.filter(x => x.venue === vv);
      let games = m.filter(x => x.venue === vv);
      let r = v.find(x => x.venue === vv);

      $('#venueInfo').innerHTML = cards([
        ['Matches', num(games.length)],
        ['First innings', num(r.innings)],
        ['Average first innings', r.innings ? (r.total / r.innings).toFixed(1) : '—'],
        ['Venue seasons', num(rows.length)]
      ]) + panel('🏟️ First-Innings Aggregate Runs By Season', 'v1', 'Scoring trends at ' + escapeHtml(vv))
        + table(games, [
          ['date', 'DATE'],
          ['team1', 'TEAM 1'],
          ['team2', 'TEAM 2'],
          ['winner', 'WINNER']
        ], 'venueCSV');

      bar('v1', rows.map(x => x.season), rows.map(x => x.total), false, iplSky);

      triggerNumberCounters();
      initScrollObserver();
    };

    if (v.length) {
      $('#venue').onchange = paint;
      paint();
    } else {
      content.innerHTML = '<div class="note scroll-reveal">⚠️ No venues in selected seasons have 5 or more first innings.</div>';
    }

  } else if (view === 'headtohead') {
    let teams = allTeams(m);
    content.innerHTML = `
      <div class="toolbar scroll-reveal">
        <div class="field">
          <label>🛡️ TEAM A</label>
          <div class="select-wrapper">
            <select id="teamA">
              ${teams.map(x => `<option>${escapeHtml(x)}</option>`).join('')}
            </select>
            <span class="select-chevron" aria-hidden="true">▼</span>
          </div>
        </div>
        <div class="field">
          <label>⚔️ TEAM B</label>
          <div class="select-wrapper">
            <select id="teamB">
              ${teams.map((x, i) => `<option ${i === 1 ? 'selected' : ''}>${escapeHtml(x)}</option>`).join('')}
            </select>
            <span class="select-chevron" aria-hidden="true">▼</span>
          </div>
        </div>
      </div>
      <div id="h2hInfo"></div>
    `;

    const paint = () => {
      let a = $('#teamA').value;
      let b = $('#teamB').value;
      let games = a === b ? [] : m.filter(x => (x.team1 === a && x.team2 === b) || (x.team1 === b && x.team2 === a));
      let aa = games.filter(x => x.winner === a).length;
      let bb = games.filter(x => x.winner === b).length;

      $('#h2hInfo').innerHTML = cards([
        ['Head-to-head', games.length],
        [a + ' wins', aa],
        [b + ' wins', bb],
        ['Other results', games.length - aa - bb]
      ]) + (games.length ? panel('⚔️ Rivalry Outcome Distribution', 'h1', `Direct face-offs between ${escapeHtml(a)} and ${escapeHtml(b)}`) : '<div class="note scroll-reveal">⚠️ Please choose two different teams with recorded matches.</div>')
        + table(games, [
          ['date', 'DATE'],
          ['season', 'SEASON'],
          ['venue', 'VENUE'],
          ['winner', 'WINNER']
        ], 'h2hCSV');

      if (games.length) {
        pie('h1', [a, b, 'No Result / Tied'], [aa, bb, games.length - aa - bb]);
      }

      triggerNumberCounters();
      initScrollObserver();
    };

    $('#teamA').onchange = paint;
    $('#teamB').onchange = paint;
    paint();

  } else if (view === 'engineering') {
    content.innerHTML = cards([
      ['Source matches', num(DATA.metadata.matches)],
      ['Delivery events', num(DATA.metadata.deliveries)],
      ['Data engine', 'PySpark 3.5.5'],
      ['Storage', 'Delta / Parquet']
    ]) + `
      <div class="panel scroll-reveal">
        <h3>💻 Big Data Architecture &amp; Lakehouse Pipeline</h3>
        <div class="note">
          <b>🏏 Cricsheet JSON → Python Ingestion → Raw CSV → Apache Spark ETL → Silver Parquet (Partitioned by Season) → Gold Analytical Parquet → Browser JSON Cache → Standalone Interactive Platform</b>
        </div>
        <p>The client application reads <code>analytics.json</code> generated via <code>python -m src.export_web</code>. Distributed ETL runs through Apache Spark via <code>python -m src.pipeline</code> for offline distributed lakehouse materialization.</p>
        
        <h3>⚡ BDC Concepts Implemented</h3>
        <p>Distributed Ingestion • DataFrames Schema Enforcement • Relational Joins &amp; Window Functions • Partitioning Strategy • Parquet Columnar Storage • Client-Side Analytical Aggregations.</p>
        
        <div class="note">
          Spark runs locally in <code>local[*]</code> mode. Hadoop native binaries support Windows filesystem I/O operations for seamless local testing.
        </div>
      </div>
    `;

    triggerNumberCounters();
    initScrollObserver();

  } else {
    // Data Sources & Provenance
    content.innerHTML = `
      <div class="panel scroll-reveal">
        <h3>📁 Data Provenance &amp; Verification</h3>
        <p>All data presented is derived from the comprehensive <a href="https://cricsheet.org/downloads/" target="_blank" rel="noopener">Cricsheet IPL Ball-by-Ball dataset</a>. Cleaned and structured using Python and Apache Spark.</p>
        <p>Schema specification reference: <a href="https://cricsheet.org/format/json/" target="_blank" rel="noopener">Cricsheet Open JSON Spec</a>.</p>
        
        <h3>🏏 Scorecard References</h3>
        <p>Match scorecards and historical context can be verified via <a href="https://www.espncricinfo.com/" target="_blank" rel="noopener">ESPNcricinfo</a>. There is zero unauthorized scraping or live polling; this is a pure analytical archive platform.</p>
        
        <h3>📊 Analytical Limitations</h3>
        <p>Historical franchise name changes (e.g., Delhi Daredevils vs Delhi Capitals) remain unmerged to honor historical integrity. No-result and tied fixtures are represented within fixture denominators.</p>
        
        <h3>⚡ Processing Metadata</h3>
        <p>Generated dataset contains <b>${num(DATA.metadata.matches)}</b> matches and <b>${num(DATA.metadata.deliveries)}</b> individual ball deliveries across 19 seasons.</p>
      </div>
    `;

    initScrollObserver();
  }

  triggerNumberCounters();
  initScrollObserver();
}

function aggregate(a, key, metrics) {
  let d = new Map();
  for (let x of a) {
    let k = x[key];
    if (!d.has(k)) d.set(k, { [key]: k, count: 0 });
    let obj = d.get(k);
    obj.count++;
    for (let m of metrics) {
      obj[m] = (obj[m] || 0) + Number(x[m] || 0);
    }
  }
  return [...d.values()];
}

function counts(a, key) {
  return aggregate(a, key, []).map(x => ({ label: x[key], count: x.count })).sort((a, b) => b.count - a.count);
}

function allTeams(a) {
  return [...new Set(a.flatMap(x => [x.team1, x.team2]).filter(Boolean))].sort();
}

// Application Lifecycle Initialization
async function init() {
  const toggle = $('#sidebarToggle');
  const setSidebarCollapsed = collapsed => {
    document.body.classList.toggle('sidebar-collapsed', collapsed);
    toggle.setAttribute('aria-expanded', String(!collapsed));
    toggle.setAttribute('aria-label', collapsed ? 'Expand sidebar menu' : 'Collapse sidebar menu');
    toggle.title = collapsed ? 'Expand sidebar menu' : 'Collapse sidebar menu';
    const label = toggle.querySelector('.toggle-label');
    if (label) label.textContent = collapsed ? 'Expand' : 'Collapse Menu';
  };

  setSidebarCollapsed(localStorage.getItem('ipl-insightx-sidebar-collapsed') === 'true');

  // Theme Toggle Engine (Day Stadium vs Night Stadium)
  const themeToggle = $('#themeToggle');
  const themeIcon = $('#themeIcon');
  const themeLabel = $('#themeLabel');

  const setTheme = (theme) => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('ipl-insightx-theme', theme);
    if (themeIcon) themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
    if (themeLabel) themeLabel.textContent = theme === 'dark' ? 'Day Stadium' : 'Night Stadium';
    render(); // Re-render charts with matching axis & grid colors
  };

  const savedTheme = localStorage.getItem('ipl-insightx-theme') || 'light';
  setTheme(savedTheme);

  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
      setTheme(currentTheme === 'dark' ? 'light' : 'dark');
    });
  }

  // Navigation Click Handlers
  document.querySelectorAll('.navitem').forEach(n => n.addEventListener('click', () => {
    view = n.dataset.view;
    location.hash = view;
    render();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }));

  $('.brand').addEventListener('click', (e) => {
    e.preventDefault();
    view = 'overview';
    location.hash = 'overview';
    render();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  toggle.addEventListener('click', () => {
    const collapsed = !document.body.classList.contains('sidebar-collapsed');
    setSidebarCollapsed(collapsed);
    localStorage.setItem('ipl-insightx-sidebar-collapsed', String(collapsed));
  });

  $('#season').onchange = e => {
    season = e.target.value;
    render();
  };

  // Scroll Progress Bar
  initScrollProgress();

  try {
    let r = await fetch('./analytics.json', { cache: 'no-store' });
    if (!r.ok) throw new Error('analytics.json is missing.');
    DATA = await r.json();

    let seasons = [...new Set(DATA.seasons.map(x => String(x.season)))].sort().reverse();
    $('#season').innerHTML = '<option value="all">🏆 All seasons (2008–2024)</option>' +
      seasons.map(s => `<option value="${escapeHtml(s)}">✨ Season ${escapeHtml(s)}</option>`).join('');

    const hash = location.hash.slice(1);
    if (document.querySelector(`[data-view="${hash}"]`)) view = hash;
    render();
  } catch (err) {
    $('#content').innerHTML = `
      <div class="empty scroll-reveal">
        <h3>🏏 First-Time Setup: Generate IPL Analytics Dataset</h3>
        <p>The frontend interface is loaded, but <code>analytics.json</code> is missing or inaccessible.</p>
        <p>From the project directory, run:</p>
        <p>
          <code>python -m src.ingestion</code><br>
          <code>python -m src.pipeline</code><br>
          <code>python -m src.export_web</code>
        </p>
        <p><small style="color:var(--accent-rose);">${escapeHtml(err.message)}</small></p>
      </div>
    `;
    initScrollObserver();
  }
}

// Start Application
init();
