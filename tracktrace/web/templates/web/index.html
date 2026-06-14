{% extends "web/base.html" %}

{% block content %}
<section class="hero" aria-labelledby="hero-h">
  <div class="wrap">
    <h1 id="hero-h">Track ocean &amp; air freight</h1>
    <p class="lede">Enter a bill of lading, booking, container, or air waybill number. We detect the carrier from the first four letters.</p>

    <form class="search" method="get" role="search" aria-label="Track a shipment">
      <div class="row">
        <div class="field">
          <label for="q">Tracking number</label>
          <input id="q" name="q" type="text" value="{{ q }}"
                 placeholder="e.g. MAEU562301487 or 160-44218904"
                 autocomplete="off" autocapitalize="characters" spellcheck="false">
        </div>
        <div class="field">
          <label for="mode">Mode</label>
          <select id="mode" name="mode">
            <option value="">Any</option>
            {% for value, name in modes %}
              <option value="{{ value }}" {% if value == mode %}selected{% endif %}>{{ name }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="field">
          <label for="carrier">Carrier</label>
          <select id="carrier" name="carrier">
            <option value="">Any carrier</option>
            {% for c in carriers %}
              <option value="{{ c.scac }}" {% if c.scac == carrier %}selected{% endif %}>{{ c.name }} ({{ c.scac }})</option>
            {% endfor %}
          </select>
        </div>
      </div>
      <div class="search-actions">
        <button class="btn" type="submit">Track shipment</button>
        {% if detected %}
          <span class="hint">Detected carrier: <strong>{{ detected.name }} ({{ detected.scac }})</strong></span>
        {% endif %}
      </div>
    </form>
  </div>
</section>

<main id="main" class="wrap">
  {% if searched %}
    <div class="results-head">
      <h2>Results</h2>
      <p class="count" role="status" aria-live="polite">{{ count }} shipment{{ count|pluralize }} found</p>
    </div>

    {% for s in shipments %}
      <article class="dossier" aria-labelledby="ref-{{ forloop.counter }}">
        <div class="d-head">
          <span class="d-ref-wrap">
            <span class="d-ref" id="ref-{{ forloop.counter }}">
              <span class="ref-kind">{{ s.ref_kind }}</span>{{ s.ref }}
            </span>
            <button class="copy-btn" type="button" data-copy="{{ s.ref }}" aria-label="Copy {{ s.ref_kind|lower }} {{ s.ref }}">
              <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>
              <span class="copy-label">Copy</span>
            </button>
          </span>
          <span class="pill mode {{ s.mode }}">{{ s.mode }}</span>
          <span class="pill status {{ s.status_class }}">{{ s.status_label }}</span>
        </div>

        <div class="route" aria-label="Route">
          <div class="route-ends">
            <span class="node origin">
              <span class="port">{{ s.origin.port }}</span>
              <span class="code">{{ s.origin.code }}</span>
            </span>
            <span class="node dest">
              <span class="port">{{ s.destination.port }}</span>
              <span class="code">{{ s.destination.code }}</span>
            </span>
          </div>
          <div class="rail">
            <span class="done" style="width: {{ s.progress }}%"></span>
            {% if s.via %}<span class="via" style="left: 50%" title="{{ s.via.port }}"></span>{% endif %}
            <span class="marker" style="left: {{ s.progress }}%"
                  role="img" aria-label="{{ s.progress }} percent of route complete"></span>
          </div>
          <div class="route-meta">
            <span class="via-label">
              {% if s.via %}via {{ s.via.port }} ({{ s.via.code }}){% else %}Direct{% endif %}
            </span>
            <span>ETA <b>{{ s.eta }}</b></span>
          </div>
        </div>

        <div class="grid four">
          <div class="kv"><div class="k">Carrier</div><div class="v">{{ s.carrier.name }}</div></div>
          <div class="kv"><div class="k">{{ s.conveyance_label }}</div><div class="v mono">{{ s.conveyance_value }}</div></div>
          <div class="kv"><div class="k">Departure</div><div class="v mono">{{ s.etd }}</div></div>
          <div class="kv"><div class="k">Arrival (est.)</div><div class="v mono">{{ s.eta }}</div></div>
        </div>

        <div class="block">
          <div class="grid">
            <div class="kv"><div class="k">Shipper</div><div class="v">{{ s.shipper.name }}<br><span class="ev-loc">{{ s.shipper.address }}</span></div></div>
            <div class="kv"><div class="k">Consignee</div><div class="v">{{ s.consignee.name }}<br><span class="ev-loc">{{ s.consignee.address }}</span></div></div>
          </div>
        </div>

        {% if s.containers %}
        <div class="block">
          <h3>Containers</h3>
          <div class="chips">
            {% for c in s.containers %}
              <button class="chip chip-btn" type="button" data-copy="{{ c.number }}" aria-label="Copy container number {{ c.number }}">{{ c.number }}<span class="t">{{ c.type }}</span></button>
            {% endfor %}
          </div>
        </div>
        {% endif %}

        {% if s.cargo %}
        <div class="block">
          <h3>Cargo</h3>
          <div class="cargo">
            {% for item in s.cargo %}
              <div class="cargo-row">
                <div>
                  <div class="desc">{{ item.description }}</div>
                  {% if item.hs_code %}<div class="hs">HS {{ item.hs_code }}</div>{% endif %}
                </div>
                <div class="qty">{{ item.pieces }} pcs · {{ item.weight_kg }} kg</div>
              </div>
            {% endfor %}
          </div>
        </div>
        {% endif %}

        {% if s.weather %}
        <div class="block">
          <h3>Weather at destination</h3>
          <div class="weather">
            <span class="temp">{{ s.weather.c }}&deg;C <span class="where">/ {{ s.weather.f }}&deg;F</span></span>
            <span class="where">{{ s.destination.city }}</span>
            <span class="wind">wind {{ s.weather.wind }} m/s</span>
          </div>
        </div>
        {% endif %}

        <div class="block">
          <h3>Milestones</h3>
          <ol class="timeline">
            {% for e in s.events %}
              <li class="{% if e.estimated %}est{% endif %}">
                <span class="dot" aria-hidden="true"></span>
                <div class="ev-top">
                  <time class="ev-time" datetime="{{ e.datetime }}">{{ e.display }}</time>
                  <span class="ev-code">{{ e.code }}</span>
                  {% if e.estimated %}<span class="ev-est">Estimated</span>{% endif %}
                </div>
                <p class="ev-desc">{{ e.description }}</p>
                {% if e.location %}<span class="ev-loc">{{ e.location }}{% if e.location_code %} <span class="lc">({{ e.location_code }})</span>{% endif %}{% if e.vessel_or_flight %} · {{ e.vessel_or_flight }}{% endif %}</span>{% endif %}
              </li>
            {% endfor %}
          </ol>
        </div>
      </article>
    {% empty %}
      <div class="empty">
        <h3>No shipments match that search</h3>
        <p>Check the number, or try a carrier or mode filter. Try a sample: <strong>MAEU562301487</strong> (ocean) or <strong>160-44218904</strong> (air).</p>
      </div>
    {% endfor %}
  {% else %}
    <div class="empty">
      <h3>Enter a number to begin</h3>
      <p>Track ocean and air shipments by reference number. Sample numbers: <strong>MAEU562301487</strong>, container <strong>MSKU0762594</strong>, or air waybill <strong>160-44218904</strong>.</p>
    </div>
  {% endif %}
</main>
{% endblock %}
