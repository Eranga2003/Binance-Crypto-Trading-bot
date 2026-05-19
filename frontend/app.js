const API_URL = 'http://localhost:5000/api';

// DOM Elements
const chartContainer = document.getElementById('tvchart');
const symbolSelect = document.getElementById('symbolSelect');
const tfButtons = document.querySelectorAll('#timeframeSelect button');
const resList = document.getElementById('resList');
const supList = document.getElementById('supList');
const statusIndicator = document.getElementById('statusIndicator');

// State
let currentSymbol = 'BTC/USDT:USDT';
let currentTimeframe = '4h';
let chart, candleSeries;
let currentPriceLines = [];

// Initialize Chart
function initChart() {
    try {
        chart = LightweightCharts.createChart(chartContainer, {
            layout: {
                background: { type: 'solid', color: 'transparent' },
                textColor: '#94a3b8',
            },
        grid: {
            vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
            horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        rightPriceScale: {
            borderColor: 'rgba(255, 255, 255, 0.1)',
        },
        timeScale: {
            borderColor: 'rgba(255, 255, 255, 0.1)',
            timeVisible: true,
        },
    });

    candleSeries = chart.addCandlestickSeries({
        upColor: '#10b981',
        downColor: '#ef4444',
        borderVisible: false,
        wickUpColor: '#10b981',
        wickDownColor: '#ef4444',
    });

    // Resize handler
    new ResizeObserver(entries => {
        if (entries.length === 0 || entries[0].target !== chartContainer) { return; }
        const newRect = entries[0].contentRect;
        chart.applyOptions({ height: newRect.height, width: newRect.width });
    }).observe(chartContainer);
    } catch(e) {
        console.error('Error initializing chart:', e);
    }
}

function updateStatus(status, text) {
    statusIndicator.className = `status ${status}`;
    statusIndicator.innerText = text;
}

function clearPriceLines() {
    currentPriceLines.forEach(line => candleSeries.removePriceLine(line));
    currentPriceLines = [];
}

function addPriceLine(price, type) {
    const color = type === 'support' ? 'rgba(16, 185, 129, 0.8)' : 'rgba(239, 68, 68, 0.8)';
    const title = type === 'support' ? 'SUP' : 'RES';
    
    const line = candleSeries.createPriceLine({
        price: price,
        color: color,
        lineWidth: 2,
        lineStyle: LightweightCharts.LineStyle.Dotted,
        axisLabelVisible: true,
        title: title,
    });
    currentPriceLines.push(line);
}

function renderSidebar(supports, resistances) {
    supList.innerHTML = supports.length ? '' : '<li>No zones found</li>';
    supports.forEach(s => {
        supList.innerHTML += `<li>
            <span>$${s.price.toFixed(2)}</span>
            <span class="level-touches">${s.touches || 'N/A'} touches</span>
        </li>`;
    });

    resList.innerHTML = resistances.length ? '' : '<li>No zones found</li>';
    resistances.forEach(r => {
        resList.innerHTML += `<li>
            <span>$${r.price.toFixed(2)}</span>
            <span class="level-touches">${r.touches || 'N/A'} touches</span>
        </li>`;
    });
}

async function fetchData() {
    updateStatus('loading', 'Loading Chart Data...');
    try {
        // Fetch OHLCV
        const dataRes = await fetch(`${API_URL}/data?symbol=${encodeURIComponent(currentSymbol)}&timeframe=${currentTimeframe}`);
        const dataObj = await dataRes.json();
        
        if (dataObj.error) throw new Error(dataObj.error);
        candleSeries.setData(dataObj.candles);
        
        // Fetch Levels
        updateStatus('loading', 'Scanning S&R Zones...');
        const levelRes = await fetch(`${API_URL}/levels?symbol=${encodeURIComponent(currentSymbol)}&timeframe=${currentTimeframe}`);
        const levelObj = await levelRes.json();
        
        if (levelObj.error) throw new Error(levelObj.error);

        // Render Levels
        clearPriceLines();
        if (levelObj.support) {
            levelObj.support.forEach(s => addPriceLine(s.price, 'support'));
        }
        if (levelObj.resistance) {
            levelObj.resistance.forEach(r => addPriceLine(r.price, 'resistance'));
        }
        
        renderSidebar(levelObj.support || [], levelObj.resistance || []);
        updateStatus('ready', 'Scan Complete');
        
    } catch (err) {
        console.error(err);
        updateStatus('error', err.message);
    }
}

// Event Listeners
symbolSelect.addEventListener('change', (e) => {
    currentSymbol = e.target.value;
    fetchData();
});

tfButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
        tfButtons.forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        currentTimeframe = e.target.getAttribute('data-tf');
        fetchData();
    });
});

// Init
initChart();
fetchData();
