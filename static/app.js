/* --------------------------------------------------
   🧠 SUPERSTORE ANALYTICS - VUE 3 CORE APPLICATION
   ES Module, Component-Driven, Pure Vanilla Async/Await
-------------------------------------------------- */

const { createApp, ref, reactive, computed, watch, onMounted, nextTick } = Vue;

const app = createApp({
    setup() {
        // --- AUTH STATE ---
        const isAuthenticated = ref(localStorage.getItem('auth_token') !== null);
        const loginData = reactive({ username: '', password: '' });
        const isLoading = ref(false);
        const loginError = ref('');

        // --- UI STATE ---
        const isDarkTheme = ref(true);
        const currentTab = ref('overview');
        const lang = ref('vi');
        const isDataLoading = ref(false);
        const searchQuery = ref('');

        // --- DATA STATE ---
        const filterOptions = reactive({ years: [], regions: [], markets: [] });
        const selectedFilters = reactive({ years: [], regions: [] });
        
        const dashboardData = reactive({
            kpis: { totalSales: 0, totalProfit: 0, profitMargin: 0, totalOrders: 0, totalQuantity: 0 },
            monthlyTrends: [],
            categorySales: [],
            regionProfit: [],
            marketSales: [],
            topProducts: [],
            transactions: []
        });

        // --- PERFORMANCE TAB DATA ---
        const performanceData = reactive({
            pareto: [],
            profitMargin: [],
            geoRevenue: [],
            subCatSales: []
        });
        const selectedDrillRegion = ref('');
        const drillTransactions = ref([]);
        const drillData = reactive({ sales: 0, profit: 0, count: 0 });

        // --- CUSTOMER PORTRAIT (RFM) DATA ---
        const customerData = reactive({
            summary: { total: 0, active: 0, attention: 0, highRisk: 0, churned: 0 },
            riskDistribution: [],
            customers: []
        });
        const customerSearchQuery = ref('');
        const selectedRiskFilter = ref('');
        const isCustomerLoading = ref(false);

        // --- SEGMENTS DATA ---
        const segmentsData = reactive({
            segmentSales: [],
            segmentProfit: [],
            segmentByRegion: [],
            segmentsList: []
        });

        // --- SHIPPING DATA ---
        const shippingData = reactive({
            summary: { avgDeliveryDays: 0, totalShippingCost: 0, avgShippingCost: 0, shippingCostRatio: 0 },
            deliveryByMode: [],
            costVsSales: [],
            performanceByRegion: []
        });

        // --- RECOMMENDATIONS DATA ---
        const recommendationsData = reactive({
            heatmap: [],
            pairs: [],
            uniqueItems: []
        });
        const selectedAnchor = ref('');

        // --- FORECAST DATA ---
        const forecastData = reactive({
            actual: [],
            forecast: [],
            kpis: { firstMonthForecast: 0, totalForecastSales: 0, totalForecastProfit: 0, growthRate: 0, startMonth: '' }
        });

        // --- AI CHAT STATE ---
        const isChatOpen = ref(false);
        const isChatTyping = ref(false);
        const chatInput = ref('');
        const chatMessages = ref([]);
        const chatBody = ref(null);

        // --- HELPER FUNCTIONS ---
        const formatNumber = (num, decimals = 2) => {
            if (num === undefined || num === null) return '0';
            return parseFloat(num).toLocaleString('en-US', {
                minimumFractionDigits: decimals,
                maximumFractionDigits: decimals
            });
        };

        const getTabLabel = (tabKey) => {
            const mapping = {
                'overview': 'Tổng Quan',
                'performance': 'Hiệu Suất Kinh Doanh',
                'customers': 'Chân Dung Khách Hàng',
                'shipping': 'Phân Tích Vận Chuyển',
                'segments': 'Phân Khúc Khách Hàng',
                'recommendations': 'Gợi Ý Sản Phẩm',
                'forecast': 'Dự Báo Tương Lai'
            };
            return mapping[tabKey] || 'Phân Hệ Mới';
        };

        // Direct ApexCharts Instances tracking
        const charts = {};

        const toggleTheme = () => {
            isDarkTheme.value = !isDarkTheme.value;
            document.body.className = isDarkTheme.value ? 'dark-theme' : 'light-theme';
            // Repaint charts with updated theme colors
            updateAllCharts();
            setTimeout(refreshIcons, 50);
        };

        const refreshIcons = () => {
            nextTick(() => {
                if (typeof lucide !== 'undefined') {
                    lucide.createIcons();
                }
            });
        };

        // --- CHART CONFIG GENERATORS ---
        // 1. Monthly Trend Options
        const trendChartSeries = computed(() => [
            { name: 'Doanh Thu', type: 'column', data: dashboardData.monthlyTrends.map(d => d.Sales) },
            { name: 'Lợi Nhuận', type: 'line', data: dashboardData.monthlyTrends.map(d => d.Profit) }
        ]);

        const trendChartOptions = computed(() => ({
            chart: { id: 'trend-chart', toolbar: { show: false }, background: 'transparent' },
            theme: { mode: isDarkTheme.value ? 'dark' : 'light' },
            colors: ['#3b82f6', '#10b981'],
            stroke: { width: [0, 3], curve: 'smooth' },
            labels: dashboardData.monthlyTrends.map(d => d['Year-Month']),
            plotOptions: { bar: { columnWidth: '50%', borderRadius: 4 } },
            grid: { borderColor: isDarkTheme.value ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' },
            legend: { position: 'top' },
            yaxis: [
                { title: { text: 'Doanh thu ($)' }, labels: { formatter: val => '$' + formatNumber(val, 0) } },
                { opposite: true, title: { text: 'Lợi nhuận ($)' }, labels: { formatter: val => '$' + formatNumber(val, 0) } }
            ]
        }));

        // 2. Category Donut Options
        const categoryChartSeries = computed(() => dashboardData.categorySales.map(d => d.sales));
        const categoryChartOptions = computed(() => ({
            chart: { id: 'category-chart', background: 'transparent' },
            theme: { mode: isDarkTheme.value ? 'dark' : 'light' },
            labels: dashboardData.categorySales.map(d => d.category),
            colors: ['#0ea5e9', '#8b5cf6', '#10b981', '#f59e0b'],
            legend: { position: 'bottom' },
            stroke: { show: false },
            dataLabels: { enabled: true, formatter: (val, opt) => `${val.toFixed(1)}%` }
        }));

        // 3. Region Profit Treemap Options
        const regionChartSeries = computed(() => [
            {
                data: dashboardData.regionProfit.map(d => ({
                    x: d.region,
                    y: d.profit
                }))
            }
        ]);
        const regionChartOptions = computed(() => ({
            chart: { id: 'region-chart', type: 'treemap', toolbar: { show: false }, background: 'transparent' },
            theme: { mode: isDarkTheme.value ? 'dark' : 'light' },
            plotOptions: {
                treemap: {
                    enableShades: true,
                    colorScale: {
                        ranges: [
                            {
                                from: -999999999,
                                to: -0.001,
                                color: '#ef4444' // Red for loss
                            },
                            {
                                from: 0,
                                to: 999999999,
                                color: '#10b981' // Green for profit
                            }
                        ]
                    }
                }
            },
            tooltip: {
                y: {
                    formatter: val => '$' + formatNumber(val, 0)
                }
            }
        }));

        // 4. Market Sales Bar Options
        const marketChartSeries = computed(() => [
            { name: 'Doanh Thu', data: dashboardData.marketSales.map(d => d.sales) }
        ]);
        const marketChartOptions = computed(() => ({
            chart: { id: 'market-chart', type: 'bar', toolbar: { show: false }, background: 'transparent' },
            theme: { mode: isDarkTheme.value ? 'dark' : 'light' },
            colors: ['#f59e0b'],
            plotOptions: { bar: { columnWidth: '60%', borderRadius: 4 } },
            xaxis: { categories: dashboardData.marketSales.map(d => d.market) },
            yaxis: { labels: { formatter: val => '$' + formatNumber(val, 0) } },
            grid: { borderColor: isDarkTheme.value ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' }
        }));

        // 5. Product Best Selling Options
        const productChartSeries = computed(() => [
            { name: 'Doanh Thu', data: dashboardData.topProducts.map(d => d.sales).reverse() }
        ]);
        const productChartOptions = computed(() => ({
            chart: { id: 'product-chart', type: 'bar', toolbar: { show: false }, background: 'transparent' },
            theme: { mode: isDarkTheme.value ? 'dark' : 'light' },
            colors: ['#06b6d4'],
            plotOptions: { bar: { horizontal: true, borderRadius: 4 } },
            xaxis: { labels: { formatter: val => '$' + formatNumber(val, 0) } },
            yaxis: { categories: dashboardData.topProducts.map(d => {
                const n = d.product;
                return n.length > 20 ? n.substring(0, 20) + '...' : n;
            }).reverse() },
            grid: { borderColor: isDarkTheme.value ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' }
        }));

        // --- FILTERED TRANSACTIONS ---
        const filteredTransactions = computed(() => {
            if (!searchQuery.value) return dashboardData.transactions;
            const q = searchQuery.value.toLowerCase();
            return dashboardData.transactions.filter(t => 
                String(t['Order ID']).toLowerCase().includes(q) ||
                String(t['Customer Name']).toLowerCase().includes(q) ||
                String(t['Product Name']).toLowerCase().includes(q) ||
                String(t['Region']).toLowerCase().includes(q) ||
                String(t['Category']).toLowerCase().includes(q)
            );
        });

        // --- CORE API ACTIONS ---
        
        const handleLogin = async () => {
            isLoading.value = true;
            loginError.value = '';
            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(loginData)
                });
                const data = await response.json();
                if (response.ok) {
                    localStorage.setItem('auth_token', data.token);
                    isAuthenticated.value = true;
                    // Bootstrap main data
                    await initializeDashboard();
                } else {
                    loginError.value = data.detail || 'Đăng nhập không thành công.';
                }
            } catch (e) {
                loginError.value = 'Lỗi kết nối máy chủ API backend.';
            } finally {
                isLoading.value = false;
                refreshIcons();
            }
        };

        const handleLogout = () => {
            localStorage.removeItem('auth_token');
            isAuthenticated.value = false;
            refreshIcons();
        };

        const fetchFilterOptions = async () => {
            try {
                const res = await fetch('/api/filters');
                const data = await res.json();
                filterOptions.years = data.years;
                filterOptions.regions = data.regions;
                filterOptions.markets = data.markets;
                
                // Default select top years & all regions
                if (selectedFilters.years.length === 0) {
                    selectedFilters.years = data.years;
                }
                if (selectedFilters.regions.length === 0) {
                    selectedFilters.regions = data.regions;
                }
            } catch (e) {
                console.error("Error loading filter options:", e);
            }
        };

        const updateAllCharts = () => {
            nextTick(() => {
                if (!isAuthenticated.value) return;
                
                // Render utility
                const repaint = (id, elId, series, options) => {
                    const el = document.getElementById(elId);
                    if (!el) return;
                    const fullOpts = { ...options, series: series };
                    if (charts[id] && el.innerHTML.trim() !== '') {
                        try {
                            charts[id].updateOptions(fullOpts, true, true);
                        } catch (e) {
                            if (charts[id]) charts[id].destroy();
                            el.innerHTML = '';
                            charts[id] = new ApexCharts(el, fullOpts);
                            charts[id].render();
                        }
                    } else {
                        if (charts[id]) charts[id].destroy();
                        el.innerHTML = '';
                        charts[id] = new ApexCharts(el, fullOpts);
                        charts[id].render();
                    }
                };

                // 1. Trend Chart
                repaint('trend', 'trend-chart-container', trendChartSeries.value, { 
                    ...trendChartOptions.value, chart: { ...trendChartOptions.value.chart, height: 320 } 
                });

                // 2. Category Chart
                repaint('category', 'category-chart-container', categoryChartSeries.value, { 
                    ...categoryChartOptions.value, chart: { ...categoryChartOptions.value.chart, type: 'donut', height: 300 } 
                });

                // 3. Region Chart
                repaint('region', 'region-chart-container', regionChartSeries.value, { 
                    ...regionChartOptions.value, chart: { ...regionChartOptions.value.chart, height: 400 } 
                });

                // 4. Market Chart
                repaint('market', 'market-chart-container', marketChartSeries.value, { 
                    ...marketChartOptions.value, chart: { ...marketChartOptions.value.chart, height: 300 } 
                });

                // 5. Product Chart
                repaint('product', 'product-chart-container', productChartSeries.value, { 
                    ...productChartOptions.value, chart: { ...productChartOptions.value.chart, height: 300 } 
                });
            });
        };

        // --- DRILL DOWN INTERACTIVE CONTROL ---
        const calculateDrilldown = () => {
            if (!selectedDrillRegion.value) {
                drillTransactions.value = [];
                drillData.sales = 0;
                drillData.profit = 0;
                drillData.count = 0;
                return;
            }
            const regionTransactions = dashboardData.transactions.filter(t => t.Region === selectedDrillRegion.value);
            drillTransactions.value = regionTransactions;
            
            const sales = regionTransactions.reduce((acc, t) => acc + (t.Sales || 0), 0);
            const profit = regionTransactions.reduce((acc, t) => acc + (t.Profit || 0), 0);
            const count = regionTransactions.length;
            
            drillData.sales = sales;
            drillData.profit = profit;
            drillData.count = count;
        };

        // --- PERFORMANCE CHARTS REPAINT ---
        const updatePerformanceCharts = () => {
            nextTick(() => {
                if (!isAuthenticated.value) return;
                
                const repaint = (id, elId, series, options) => {
                    const el = document.getElementById(elId);
                    if (!el) return;
                    const fullOpts = { ...options, series: series };
                    if (charts[id] && el.innerHTML.trim() !== '') {
                        try {
                            charts[id].updateOptions(fullOpts, true, true);
                        } catch (e) {
                            if (charts[id]) charts[id].destroy();
                            el.innerHTML = '';
                            charts[id] = new ApexCharts(el, fullOpts);
                            charts[id].render();
                        }
                    } else {
                        if (charts[id]) charts[id].destroy();
                        el.innerHTML = '';
                        charts[id] = new ApexCharts(el, fullOpts);
                        charts[id].render();
                    }
                };

                // 1. Pareto Chart
                repaint('pareto', 'pareto-chart-container', [
                    { name: 'Doanh Thu', type: 'column', data: performanceData.pareto.map(p => p.sales) },
                    { name: 'Phần Trăm Tích Lũy', type: 'line', data: performanceData.pareto.map(p => p.cumPercent) }
                ], {
                    chart: { id: 'pareto-chart', toolbar: { show: false }, background: 'transparent' },
                    theme: { mode: isDarkTheme.value ? 'dark' : 'light' },
                    colors: ['#06b6d4', '#ef4444'],
                    stroke: { width: [0, 3], curve: 'smooth' },
                    labels: performanceData.pareto.map(p => p.customer),
                    plotOptions: { bar: { columnWidth: '60%', borderRadius: 4 } },
                    grid: { borderColor: isDarkTheme.value ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' },
                    yaxis: [
                        { title: { text: 'Doanh thu ($)' }, labels: { formatter: val => '$' + formatNumber(val, 0) } },
                        { opposite: true, max: 100, title: { text: 'Tích lũy (%)' }, labels: { formatter: val => val.toFixed(0) + '%' } }
                    ]
                });

                // 2. Margin Chart
                repaint('margin', 'margin-chart-container', [
                    { name: 'Biên Lợi Nhuận (%)', data: performanceData.profitMargin.map(m => m.margin) }
                ], {
                    chart: { id: 'margin-chart', type: 'bar', height: 450, toolbar: { show: false }, background: 'transparent' },
                    theme: { mode: isDarkTheme.value ? 'dark' : 'light' },
                    colors: ['#10b981'],
                    plotOptions: { bar: { horizontal: true, borderRadius: 4 } },
                    dataLabels: { enabled: false },
                    xaxis: { categories: performanceData.profitMargin.map(m => m.region), labels: { formatter: val => val.toFixed(1) + '%' } },
                    tooltip: { y: { formatter: val => val.toFixed(2) + '%' } },
                    grid: { borderColor: isDarkTheme.value ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' }
                });

                // 3. Sub-Category Chart
                repaint('subcat', 'subcat-chart-container', [
                    { name: 'Doanh Thu', data: performanceData.subCatSales.map(s => s.sales) }
                ], {
                    chart: { id: 'subcat-chart', type: 'bar', height: 450, toolbar: { show: false }, background: 'transparent' },
                    theme: { mode: isDarkTheme.value ? 'dark' : 'light' },
                    colors: ['#a855f7'],
                    plotOptions: { bar: { horizontal: true, borderRadius: 4 } },
                    xaxis: { categories: performanceData.subCatSales.map(s => s.subCategory), labels: { formatter: val => '$' + formatNumber(val, 0) } },
                    grid: { borderColor: isDarkTheme.value ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' }
                });

                // 4. Geo Revenue Chart
                repaint('geo', 'geo-chart-container', [
                    { name: 'Doanh Thu', data: performanceData.geoRevenue.map(g => g.sales) }
                ], {
                    chart: { id: 'geo-chart', type: 'bar', height: 600, toolbar: { show: false }, background: 'transparent' },
                    theme: { mode: isDarkTheme.value ? 'dark' : 'light' },
                    colors: ['#f59e0b'],
                    plotOptions: { bar: { horizontal: true, borderRadius: 4 } },
                    xaxis: { categories: performanceData.geoRevenue.map(g => `${g.market} - ${g.region}`), labels: { formatter: val => '$' + formatNumber(val, 0) } },
                    grid: { borderColor: isDarkTheme.value ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' }
                });
            });
        };

        const fetchPerformanceData = async () => {
            isDataLoading.value = true;
            try {
                const res = await fetch('/api/dashboard/performance', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        years: selectedFilters.years,
                        regions: selectedFilters.regions
                    })
                });
                const data = await res.json();
                performanceData.pareto = data.pareto;
                performanceData.profitMargin = data.profitMargin;
                performanceData.geoRevenue = data.geoRevenue;
                performanceData.subCatSales = data.subCatSales;
                
                isDataLoading.value = false;
                await nextTick();
                updatePerformanceCharts();
            } catch (e) {
                console.error("Error loading performance data:", e);
            } finally {
                isDataLoading.value = false;
                refreshIcons();
            }
        };

        // --- CUSTOMER PORTRAIT (RFM) FUNCTIONS ---
        const updateCustomerCharts = () => {
            nextTick(() => {
                if (!isAuthenticated.value) return;
                
                const el = document.getElementById('risk-distribution-chart-container');
                if (!el) return;
                
                const series = [
                    customerData.summary.active,
                    customerData.summary.attention,
                    customerData.summary.highRisk,
                    customerData.summary.churned
                ];
                
                const fullOpts = {
                    chart: { id: 'customer-risk-chart', type: 'donut', height: 320, background: 'transparent' },
                    theme: { mode: isDarkTheme.value ? 'dark' : 'light' },
                    labels: ['An toàn (Active)', 'Cần chú ý (Needs Attention)', 'Nguy cơ cao (High Risk)', 'Đã rời bỏ (Churned)'],
                    colors: ['#10b981', '#f59e0b', '#ef4444', '#6b7280'],
                    legend: { position: 'bottom' },
                    stroke: { show: false },
                    dataLabels: { enabled: true, formatter: (val, opt) => `${val.toFixed(1)}%` },
                    series: series
                };
                
                if (charts['customer-risk'] && el.innerHTML.trim() !== '') {
                    try {
                        charts['customer-risk'].updateOptions(fullOpts, true, true);
                    } catch (e) {
                        if (charts['customer-risk']) charts['customer-risk'].destroy();
                        el.innerHTML = '';
                        charts['customer-risk'] = new ApexCharts(el, fullOpts);
                        charts['customer-risk'].render();
                    }
                } else {
                    if (charts['customer-risk']) charts['customer-risk'].destroy();
                    el.innerHTML = '';
                    charts['customer-risk'] = new ApexCharts(el, fullOpts);
                    charts['customer-risk'].render();
                }
            });
        };

        const fetchCustomerData = async () => {
            isDataLoading.value = true;
            try {
                const res = await fetch('/api/dashboard/customers', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        years: selectedFilters.years,
                        regions: selectedFilters.regions
                    })
                });
                const data = await res.json();
                customerData.summary = data.summary;
                customerData.riskDistribution = data.riskDistribution;
                customerData.customers = data.customers;
                
                isDataLoading.value = false;
                await nextTick();
                updateCustomerCharts();
            } catch (e) {
                console.error("Error loading customer data:", e);
            } finally {
                isDataLoading.value = false;
                refreshIcons();
            }
        };

        // --- SEGMENTS FUNCTIONS ---
        const updateSegmentsCharts = () => {
            nextTick(() => {
                if (!isAuthenticated.value) return;
                
                const repaint = (id, elId, series, options) => {
                    const el = document.getElementById(elId);
                    if (!el) return;
                    const fullOpts = { ...options, series: series };
                    if (charts[id] && el.innerHTML.trim() !== '') {
                        try {
                            charts[id].updateOptions(fullOpts, true, true);
                        } catch (e) {
                            if (charts[id]) charts[id].destroy();
                            el.innerHTML = '';
                            charts[id] = new ApexCharts(el, fullOpts);
                            charts[id].render();
                        }
                    } else {
                        if (charts[id]) charts[id].destroy();
                        el.innerHTML = '';
                        charts[id] = new ApexCharts(el, fullOpts);
                        charts[id].render();
                    }
                };

                // 1. Segment Sales Pie Chart
                if (document.getElementById('segment-sales-chart-container')) {
                    repaint('segment-sales', 'segment-sales-chart-container', segmentsData.segmentSales.map(d => d.sales), {
                        chart: { id: 'segment-sales-chart', type: 'pie', height: 320, background: 'transparent' },
                        theme: { mode: isDarkTheme.value ? 'dark' : 'light' },
                        labels: segmentsData.segmentSales.map(d => d.segment),
                        colors: ['#0ea5e9', '#8b5cf6', '#10b981', '#f59e0b'],
                        legend: { position: 'bottom' },
                        stroke: { show: false },
                        dataLabels: { enabled: true, formatter: (val) => `${val.toFixed(1)}%` }
                    });
                }

                // 2. Segment Profit Bar Chart
                if (document.getElementById('segment-profit-chart-container')) {
                    repaint('segment-profit', 'segment-profit-chart-container', [
                        { name: 'Lợi Nhuận', data: segmentsData.segmentProfit.map(d => d.profit) }
                    ], {
                        chart: { id: 'segment-profit-chart', type: 'bar', toolbar: { show: false }, background: 'transparent' },
                        theme: { mode: isDarkTheme.value ? 'dark' : 'light' },
                        colors: ['#f59e0b'],
                        plotOptions: { bar: { horizontal: false, columnWidth: '50%', borderRadius: 4 } },
                        xaxis: { categories: segmentsData.segmentProfit.map(d => d.segment) },
                        yaxis: { labels: { formatter: val => '$' + formatNumber(val, 0) } },
                        grid: { borderColor: isDarkTheme.value ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' }
                    });
                }

                // 3. Segment by Region Stacked Bar Chart
                if (document.getElementById('segment-region-chart-container')) {
                    const regionSeries = segmentsData.segmentsList.map(seg => {
                        return {
                            name: seg,
                            data: segmentsData.segmentByRegion.map(r => r[seg] || 0)
                        };
                    });
                    
                    repaint('segment-region', 'segment-region-chart-container', regionSeries, {
                        chart: { id: 'segment-region-chart', type: 'bar', stacked: true, stackType: '100%', height: 600, toolbar: { show: false }, background: 'transparent' },
                        theme: { mode: isDarkTheme.value ? 'dark' : 'light' },
                        colors: ['#0ea5e9', '#8b5cf6', '#10b981', '#f59e0b'],
                        plotOptions: { bar: { horizontal: true, borderRadius: 2 } },
                        dataLabels: { enabled: false },
                        xaxis: { categories: segmentsData.segmentByRegion.map(r => r.Region), labels: { formatter: val => val + '%' } },
                        tooltip: { y: { formatter: val => '$' + formatNumber(val, 0) } },
                        grid: { borderColor: isDarkTheme.value ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' }
                    });
                }
            });
        };

        const fetchSegmentsData = async () => {
            isDataLoading.value = true;
            try {
                const res = await fetch('/api/dashboard/segments', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        years: selectedFilters.years,
                        regions: selectedFilters.regions
                    })
                });
                const data = await res.json();
                segmentsData.segmentSales = data.segmentSales;
                segmentsData.segmentProfit = data.segmentProfit;
                segmentsData.segmentByRegion = data.segmentByRegion;
                segmentsData.segmentsList = data.segmentsList;
                
                isDataLoading.value = false;
                await nextTick();
                updateSegmentsCharts();
            } catch (e) {
                console.error("Error loading segment data:", e);
            } finally {
                isDataLoading.value = false;
                refreshIcons();
            }
        };

        // --- SHIPPING FUNCTIONS ---
        const updateShippingCharts = () => {
            const repaint = (id, elId, series, options) => {
                const el = document.getElementById(elId);
                if (!el) return;
                const fullOpts = { ...options, series: series };
                if (charts[id] && el.innerHTML.trim() !== '') {
                    try {
                        charts[id].updateOptions(fullOpts, true, true);
                    } catch (e) {
                        if (charts[id]) charts[id].destroy();
                        el.innerHTML = '';
                        charts[id] = new ApexCharts(el, fullOpts);
                        charts[id].render();
                    }
                } else {
                    if (charts[id]) charts[id].destroy();
                    el.innerHTML = '';
                    charts[id] = new ApexCharts(el, fullOpts);
                    charts[id].render();
                }
            };

            // 1. Box Plot: Delivery Days by Ship Mode
            if (document.getElementById('ship-mode-box-chart-container')) {
                const boxSeries = [{
                    type: 'boxPlot',
                    data: shippingData.deliveryByMode.map(d => ({
                        x: d.mode,
                        y: [d.min, d.q1, d.median, d.q3, d.max]
                    }))
                }];
                repaint('ship-mode-box', 'ship-mode-box-chart-container', boxSeries, {
                    chart: { id: 'ship-mode-box-chart', type: 'boxPlot', height: 320, background: 'transparent', toolbar: {show: false} },
                    theme: { mode: isDarkTheme.value ? 'dark' : 'light' },
                    colors: ['#0ea5e9'],
                    grid: { borderColor: isDarkTheme.value ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' }
                });
            }

            // 2. Scatter Plot: Cost vs Sales
            if (document.getElementById('cost-sales-scatter-chart-container')) {
                // Group by priority for color coding
                const priorityGroups = {};
                shippingData.costVsSales.forEach(d => {
                    if (!priorityGroups[d.priority]) priorityGroups[d.priority] = [];
                    priorityGroups[d.priority].push([d.sales, d.cost]);
                });
                
                const scatterSeries = Object.keys(priorityGroups).map(p => ({
                    name: p,
                    data: priorityGroups[p]
                }));

                repaint('cost-sales-scatter', 'cost-sales-scatter-chart-container', scatterSeries, {
                    chart: { id: 'cost-sales-scatter-chart', type: 'scatter', height: 350, background: 'transparent', toolbar: {show: false} },
                    theme: { mode: isDarkTheme.value ? 'dark' : 'light' },
                    colors: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'],
                    xaxis: { title: { text: 'Doanh Số ($)' }, tickAmount: 5, labels: { formatter: val => '$' + formatNumber(val, 0) } },
                    yaxis: { title: { text: 'Chi Phí Ship ($)' }, labels: { formatter: val => '$' + formatNumber(val, 0) } },
                    grid: { borderColor: isDarkTheme.value ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' }
                });
            }

            // 3. Bar Chart: Delivery Days by Region
            if (document.getElementById('ship-region-days-chart-container')) {
                repaint('ship-region-days', 'ship-region-days-chart-container', [{
                    name: 'Ngày Giao Trung Bình',
                    data: shippingData.performanceByRegion.map(d => d.avgDeliveryDays)
                }], {
                    chart: { id: 'ship-region-days-chart', type: 'bar', height: 600, background: 'transparent', toolbar: {show: false} },
                    theme: { mode: isDarkTheme.value ? 'dark' : 'light' },
                    colors: ['#f59e0b'],
                    xaxis: { categories: shippingData.performanceByRegion.map(d => d.region) },
                    plotOptions: { bar: { horizontal: true, borderRadius: 4, dataLabels: { position: 'top' } } },
                    dataLabels: { enabled: true, formatter: val => formatNumber(val, 1) + ' ngày', offsetX: 30, style: { colors: [isDarkTheme.value ? '#e5e7eb' : '#374151'] } },
                    grid: { borderColor: isDarkTheme.value ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' }
                });
            }

            // 4. Bar Chart: Shipping Cost by Region
            if (document.getElementById('ship-region-cost-chart-container')) {
                repaint('ship-region-cost', 'ship-region-cost-chart-container', [{
                    name: 'Chi Phí Trung Bình',
                    data: shippingData.performanceByRegion.map(d => d.avgShippingCost)
                }], {
                    chart: { id: 'ship-region-cost-chart', type: 'bar', height: 600, background: 'transparent', toolbar: {show: false} },
                    theme: { mode: isDarkTheme.value ? 'dark' : 'light' },
                    colors: ['#0ea5e9'],
                    xaxis: { categories: shippingData.performanceByRegion.map(d => d.region), labels: { formatter: val => '$' + formatNumber(val, 0) } },
                    plotOptions: { bar: { horizontal: true, borderRadius: 4, dataLabels: { position: 'top' } } },
                    dataLabels: { enabled: true, formatter: val => '$' + formatNumber(val, 2), offsetX: 30, style: { colors: [isDarkTheme.value ? '#e5e7eb' : '#374151'] } },
                    grid: { borderColor: isDarkTheme.value ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' }
                });
            }
        };

        const fetchShippingData = async () => {
            isDataLoading.value = true;
            try {
                const res = await fetch('/api/dashboard/shipping', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        years: selectedFilters.years,
                        regions: selectedFilters.regions
                    })
                });
                const data = await res.json();
                shippingData.summary = data.summary;
                shippingData.deliveryByMode = data.deliveryByMode;
                shippingData.costVsSales = data.costVsSales;
                shippingData.performanceByRegion = data.performanceByRegion;
                
                isDataLoading.value = false;
                await nextTick();
                updateShippingCharts();
            } catch (e) {
                console.error("Error loading shipping data:", e);
            } finally {
                isDataLoading.value = false;
                refreshIcons();
            }
        };

        // --- RECOMMENDATIONS FUNCTIONS ---
        const updateRecommendationsCharts = () => {
            const repaint = (id, elId, series, options) => {
                const el = document.getElementById(elId);
                if (!el) return;
                const fullOpts = { ...options, series: series };
                if (charts[id] && el.innerHTML.trim() !== '') {
                    try { charts[id].updateOptions(fullOpts, true, true); }
                    catch (e) { charts[id].destroy(); el.innerHTML = ''; charts[id] = new ApexCharts(el, fullOpts); charts[id].render(); }
                } else {
                    if (charts[id]) charts[id].destroy();
                    el.innerHTML = ''; charts[id] = new ApexCharts(el, fullOpts); charts[id].render();
                }
            };

            if (document.getElementById('co-occurrence-heatmap-container')) {
                // Group heatmap data by 'x'
                const grouped = {};
                recommendationsData.heatmap.forEach(d => {
                    if (!grouped[d.x]) grouped[d.x] = [];
                    grouped[d.x].push({ x: d.y, y: d.val });
                });
                const series = Object.keys(grouped).map(k => ({ name: k, data: grouped[k] }));

                repaint('heatmap', 'co-occurrence-heatmap-container', series, {
                    chart: { id: 'heatmap-chart', type: 'heatmap', height: 600, background: 'transparent', toolbar: {show: false} },
                    theme: { mode: isDarkTheme.value ? 'dark' : 'light' },
                    colors: ['#0d9488'],
                    dataLabels: { enabled: false },
                    grid: { borderColor: isDarkTheme.value ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' }
                });
            }
        };

        const fetchRecommendationsData = async () => {
            isDataLoading.value = true;
            try {
                const res = await fetch('/api/dashboard/recommendations', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ years: selectedFilters.years, regions: selectedFilters.regions })
                });
                const data = await res.json();
                recommendationsData.heatmap = data.heatmap;
                recommendationsData.pairs = data.pairs;
                recommendationsData.uniqueItems = data.uniqueItems;
                if (!selectedAnchor.value && data.uniqueItems.length > 0) {
                    selectedAnchor.value = data.uniqueItems[0];
                }
                
                isDataLoading.value = false;
                await nextTick();
                updateRecommendationsCharts();
            } catch (e) {
                console.error("Error loading recommendations:", e);
            } finally {
                isDataLoading.value = false;
                refreshIcons();
            }
        };

        const filteredComboRecs = computed(() => {
            if (!selectedAnchor.value) return [];
            return recommendationsData.pairs.filter(p => p.itemA === selectedAnchor.value || p.itemB === selectedAnchor.value).map(p => {
                const isA = p.itemA === selectedAnchor.value;
                return {
                    suggestedItem: isA ? p.itemB : p.itemA,
                    count: p.count,
                    confidence: (isA ? p.confAB : p.confBA) * 100
                };
            }).sort((a, b) => b.confidence - a.confidence);
        });

        // --- FORECAST FUNCTIONS ---
        const updateForecastCharts = () => {
            const repaint = (id, elId, series, options) => {
                const el = document.getElementById(elId);
                if (!el) return;
                const fullOpts = { ...options, series: series };
                if (charts[id] && el.innerHTML.trim() !== '') {
                    try { charts[id].updateOptions(fullOpts, true, true); }
                    catch (e) { charts[id].destroy(); el.innerHTML = ''; charts[id] = new ApexCharts(el, fullOpts); charts[id].render(); }
                } else {
                    if (charts[id]) charts[id].destroy();
                    el.innerHTML = ''; charts[id] = new ApexCharts(el, fullOpts); charts[id].render();
                }
            };

            if (document.getElementById('forecast-chart-container') && forecastData.actual.length > 0) {
                // Combine actual and forecast for lines
                const actualSeries = {
                    name: 'Doanh Số Thực Tế',
                    type: 'line',
                    data: forecastData.actual.map(d => ({ x: d.month, y: d.sales }))
                };
                const forecastSeries = {
                    name: 'Doanh Số Dự Báo',
                    type: 'line',
                    data: forecastData.forecast.map(d => ({ x: d.month, y: d.sales }))
                };
                
                // For area (confidence interval), apexcharts uses rangeArea or we can just use regular area
                // Using two area series for bounds is simpler
                const upperBound = {
                    name: 'Cận Trên (95%)',
                    type: 'line',
                    data: forecastData.forecast.map(d => ({ x: d.month, y: d.upper }))
                };
                const lowerBound = {
                    name: 'Cận Dưới (95%)',
                    type: 'line',
                    data: forecastData.forecast.map(d => ({ x: d.month, y: d.lower }))
                };

                repaint('forecast-chart', 'forecast-chart-container', [actualSeries, forecastSeries, upperBound, lowerBound], {
                    chart: { id: 'forecast-line-chart', type: 'line', height: 450, background: 'transparent', toolbar: {show: false} },
                    theme: { mode: isDarkTheme.value ? 'dark' : 'light' },
                    stroke: { width: [3, 3, 1, 1], dashArray: [0, 5, 2, 2] },
                    colors: ['#3b82f6', '#f59e0b', '#fbbf24', '#fbbf24'],
                    xaxis: { type: 'category' },
                    yaxis: { labels: { formatter: val => '$' + formatNumber(val, 0) } },
                    grid: { borderColor: isDarkTheme.value ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' },
                    fill: { type: 'solid', opacity: [1, 1, 0.1, 0.1] }
                });
            }
        };

        const fetchForecastData = async () => {
            isDataLoading.value = true;
            try {
                const res = await fetch('/api/dashboard/forecast', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ years: selectedFilters.years, regions: selectedFilters.regions })
                });
                const data = await res.json();
                forecastData.actual = data.actual;
                forecastData.forecast = data.forecast;
                forecastData.kpis = data.kpis;
                
                isDataLoading.value = false;
                await nextTick();
                updateForecastCharts();
            } catch (e) {
                console.error("Error loading forecast data:", e);
            } finally {
                isDataLoading.value = false;
                refreshIcons();
            }
        };

        const filteredCustomers = computed(() => {
            let list = customerData.customers;
            if (customerSearchQuery.value) {
                const q = customerSearchQuery.value.toLowerCase();
                list = list.filter(c => 
                    String(c['Customer Name'] || '').toLowerCase().includes(q) ||
                    String(c['Customer ID'] || '').toLowerCase().includes(q)
                );
            }
            if (selectedRiskFilter.value) {
                list = list.filter(c => c.Churn_Risk === selectedRiskFilter.value);
            }
            return list;
        });

        // --- DYNAMIC CENTRALIZED DATA FETCH ---
        const fetchDashboardData = async () => {
            isDataLoading.value = true;
            try {
                if (currentTab.value === 'overview') {
                    const res = await fetch('/api/dashboard/overview', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            years: selectedFilters.years,
                            regions: selectedFilters.regions
                        })
                    });
                    const data = await res.json();
                    dashboardData.kpis = data.kpis;
                    dashboardData.monthlyTrends = data.monthlyTrends;
                    dashboardData.categorySales = data.categorySales;
                    dashboardData.regionProfit = data.regionProfit;
                    dashboardData.marketSales = data.marketSales;
                    dashboardData.topProducts = data.topProducts;
                    dashboardData.transactions = data.transactions;
                    
                    isDataLoading.value = false;
                    await nextTick();
                    updateAllCharts();
                } else if (currentTab.value === 'performance') {
                    await fetchPerformanceData();
                } else if (currentTab.value === 'customers') {
                    await fetchCustomerData();
                } else if (currentTab.value === 'segments') {
                    await fetchSegmentsData();
                } else if (currentTab.value === 'shipping') {
                    await fetchShippingData();
                } else if (currentTab.value === 'recommendations') {
                    await fetchRecommendationsData();
                } else if (currentTab.value === 'forecast') {
                    await fetchForecastData();
                }
            } catch (e) {
                console.error("Error loading dataset:", e);
            } finally {
                isDataLoading.value = false;
                refreshIcons();
            }
        };

        const initializeDashboard = async () => {
            await fetchFilterOptions();
            await fetchDashboardData();
        };

        // --- CHATBOT ACTIONS ---
        const toggleChat = () => {
            isChatOpen.value = !isChatOpen.value;
            if (isChatOpen.value) {
                refreshIcons();
                scrollToBottom();
            }
        };

        const scrollToBottom = () => {
            nextTick(() => {
                if (chatBody.value) {
                    chatBody.value.scrollTop = chatBody.value.scrollHeight;
                }
            });
        };

        const renderMarkdown = (text) => {
            if (!text) return '';
            // Extremely primitive Markdown to HTML rendering to keep it Zero-Node
            let html = text
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // bold
                .replace(/\*(.*?)\*/g, '<em>$1</em>') // italic
                .replace(/`([^`]+)`/g, '<code>$1</code>') // inline code
                .replace(/^### (.*?)$/gm, '<h3>$1</h3>') // H3
                .replace(/^## (.*?)$/gm, '<h2>$1</h2>') // H2
                .replace(/^# (.*?)$/gm, '<h1>$1</h1>') // H1
                .replace(/^- (.*?)$/gm, '<li>$1</li>'); // bullet list
            
            return html;
        };

        const sendChatMessage = async () => {
            if (!chatInput.value.trim()) return;
            
            const userMsg = chatInput.value;
            chatMessages.value.push({ role: 'user', content: userMsg });
            chatInput.value = '';
            isChatTyping.value = true;
            scrollToBottom();

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: userMsg, language: lang.value })
                });
                const data = await res.json();
                chatMessages.value.push({ role: 'bot', content: data.response });
            } catch (e) {
                chatMessages.value.push({ role: 'bot', content: '⚠️ Rất tiếc, em không thể kết nối với máy chủ API AI lúc này.' });
            } finally {
                isChatTyping.value = false;
                scrollToBottom();
            }
        };

        // --- MOUNTED INITIALIZATION ---
        onMounted(() => {
            refreshIcons();
            if (isAuthenticated.value) {
                initializeDashboard();
            }
        });

        // Watch for Tab switching to dynamically repaint DOM or charts
        watch(currentTab, (newTab) => {
            refreshIcons();
            if (newTab === 'overview') {
                updateAllCharts();
            } else if (newTab === 'performance') {
                fetchPerformanceData();
            } else if (newTab === 'customers') {
                fetchCustomerData();
            } else if (newTab === 'segments') {
                fetchSegmentsData();
            } else if (newTab === 'shipping') {
                fetchShippingData();
            } else if (newTab === 'recommendations') {
                fetchRecommendationsData();
            } else if (newTab === 'forecast') {
                fetchForecastData();
            }
        });

        return {
            // Auth
            isAuthenticated, loginData, isLoading, loginError, handleLogin, handleLogout,
            // UI State
            isDarkTheme, currentTab, lang, isDataLoading, searchQuery, toggleTheme, formatNumber, getTabLabel,
            // Filters & Data
            filterOptions, selectedFilters, dashboardData, fetchDashboardData,
            filteredTransactions,
            // Chart Option Computed Refs
            trendChartSeries, trendChartOptions,
            categoryChartSeries, categoryChartOptions,
            regionChartSeries, regionChartOptions,
            marketChartSeries, marketChartOptions,
            productChartSeries, productChartOptions,
            // Chat
            isChatOpen, isChatTyping, chatInput, chatMessages, chatBody,
            toggleChat, sendChatMessage, renderMarkdown,
            // Performance Tab
            performanceData, selectedDrillRegion, drillTransactions, drillData, calculateDrilldown,
            // Customers Tab
            customerData, customerSearchQuery, selectedRiskFilter, filteredCustomers, fetchCustomerData,
            // Segments Tab
            segmentsData, fetchSegmentsData,
            // Shipping Tab
            shippingData, fetchShippingData,
            // Recommendations Tab
            recommendationsData, selectedAnchor, filteredComboRecs, fetchRecommendationsData,
            // Forecast Tab
            forecastData, fetchForecastData
        };
    }
});

// Mount the app natively (Wrapper discarded for Vanilla Performance)
app.mount('#app');
