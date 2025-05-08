/**
 * Theme: Arclon - Responsive Bootstrap 5 Admin Dashboard
 * Author: Coderthemes
 * Module/App: Apex Column Charts
 */

//
// BASIC COLUMN CHART
//
var colors = ['#5b69bc', '#30cf46', '#fa5c7c'];
var dataColors = $('#basic-column').data('colors');
if (dataColors) {
	colors = dataColors.split(',');
}
var options = {
	chart: {
		height: 396,
		type: 'bar',
		toolbar: {
			show: false
		}
	},
	plotOptions: {
		bar: {
			horizontal: false,
			endingShape: 'rounded',
			columnWidth: '55%'
		}
	},
	dataLabels: {
		enabled: false
	},
	stroke: {
		show: true,
		width: 2,
		colors: ['transparent']
	},
	colors: colors,
	series: [
		{
			name: 'Net Profit',
			data: [44, 55, 57, 56, 61, 58, 63, 60, 66]
		},
		{
			name: 'Revenue',
			data: [76, 85, 101, 98, 87, 105, 91, 114, 94]
		},
		{
			name: 'Free Cash Flow',
			data: [35, 41, 36, 26, 45, 48, 52, 53, 41]
		}
	],
	xaxis: {
		categories: ['Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct']
	},
	legend: {
		offsetY: 7
	},
	yaxis: {
		title: {
			text: '$ (thousands)'
		}
	},
	fill: {
		opacity: 1
	},
	grid: {
		row: {
			colors: ['transparent', 'transparent'], // takes an array which will be repeated on columns
			opacity: 0.2
		},
		borderColor: '#f1f3fa',
		padding: {
			bottom: 5
		}
	},
	tooltip: {
		y: {
			formatter: function (val) {
				return '$ ' + val + ' thousands';
			}
		}
	}
};

var chart = new ApexCharts(document.querySelector('#basic-column'), options);

chart.render();

//
// COLUMN CHART WITH DATALABELS
//
var colors = ['#5b69bc'];
var dataColors = $('#datalabels-column').data('colors');
if (dataColors) {
	colors = dataColors.split(',');
}
var options = {
	chart: {
		height: 380,
		type: 'bar',
		toolbar: {
			show: false
		}
	},
	plotOptions: {
		bar: {
			borderRadius: 10,
			dataLabels: {
				position: 'top' // top, center, bottom
			}
		}
	},
	dataLabels: {
		enabled: true,
		formatter: function (val) {
			return val + '%';
		},
		offsetY: -25,
		style: {
			fontSize: '12px',
			colors: ['#304758']
		}
	},
	colors: colors,
	legend: {
		show: true,
		horizontalAlign: 'center',
		offsetX: 0,
		offsetY: -5
	},
	series: [
		{
			name: 'Inflation',
			data: [2.3, 3.1, 4.0, 10.1, 4.0, 3.6, 3.2, 2.3, 1.4, 0.8, 0.5, 0.2]
		}
	],
	xaxis: {
		categories: [
			'Jan',
			'Feb',
			'Mar',
			'Apr',
			'May',
			'Jun',
			'Jul',
			'Aug',
			'Sep',
			'Oct',
			'Nov',
			'Dec'
		],
		position: 'top',
		labels: {
			offsetY: 0
		},
		axisBorder: {
			show: false
		},
		axisTicks: {
			show: false
		},
		crosshairs: {
			fill: {
				type: 'gradient',
				gradient: {
					colorFrom: '#D8E3F0',
					colorTo: '#BED1E6',
					stops: [0, 100],
					opacityFrom: 0.4,
					opacityTo: 0.5
				}
			}
		},
		tooltip: {
			enabled: true,
			offsetY: -10
		}
	},
	fill: {
		gradient: {
			enabled: false,
			shade: 'light',
			type: 'horizontal',
			shadeIntensity: 0.25,
			gradientToColors: undefined,
			inverseColors: true,
			opacityFrom: 1,
			opacityTo: 1,
			stops: [50, 0, 100, 100]
		}
	},
	yaxis: {
		axisBorder: {
			show: false
		},
		axisTicks: {
			show: false
		},
		labels: {
			show: false,
			formatter: function (val) {
				return val + '%';
			}
		}
	},
	title: {
		text: 'Monthly Inflation in Argentina, 2002',
		floating: true,
		offsetY: 360,
		align: 'center',
		style: {
			color: '#444'
		}
	},
	grid: {
		row: {
			colors: ['transparent', 'transparent'], // takes an array which will be repeated on columns
			opacity: 0.2
		},
		borderColor: '#f1f3fa'
	}
};

var chart = new ApexCharts(document.querySelector('#datalabels-column'), options);

chart.render();

//
// STACKED COLUMN CHART
//

var colors = ['#39afd1', '#faae37', '#e3eaef'];
var dataColors = $('#stacked-column').data('colors');
if (dataColors) {
	colors = dataColors.split(',');
}
var options = {
	chart: {
		height: 380,
		type: 'bar',
		stacked: true,
		toolbar: {
			show: false
		}
	},
	plotOptions: {
		bar: {
			horizontal: false,
			columnWidth: '50%'
		}
	},
	series: [
		{
			name: 'Product A',
			data: [44, 55, 41, 67, 22, 43, 21, 49]
		},
		{
			name: 'Product B',
			data: [13, 23, 20, 8, 13, 27, 33, 12]
		},
		{
			name: 'Product C',
			data: [11, 17, 15, 15, 21, 14, 15, 13]
		}
	],
	xaxis: {
		categories: [
			'2011 Q1',
			'2011 Q2',
			'2011 Q3',
			'2011 Q4',
			'2012 Q1',
			'2012 Q2',
			'2012 Q3',
			'2012 Q4'
		]
	},
	colors: colors,
	fill: {
		opacity: 1
	},
	legend: {
		offsetY: 7
	},
	grid: {
		row: {
			colors: ['transparent', 'transparent'], // takes an array which will be repeated on columns
			opacity: 0.2
		},
		borderColor: '#f1f3fa',
		padding: {
			bottom: 5
		}
	}
};

var chart = new ApexCharts(document.querySelector('#stacked-column'), options);

chart.render();

//
// 100% STACKED COLUMN CHART
//
var colors = ['#39afd1', '#30cf46', '#e3eaef'];
var dataColors = $('#full-stacked-column').data('colors');
if (dataColors) {
	colors = dataColors.split(',');
}
var options = {
	chart: {
		height: 380,
		type: 'bar',
		stacked: true,
		stackType: '100%',
		toolbar: {
			show: false
		}
	},
	plotOptions: {
		bar: {
			columnWidth: '50%'
		}
	},
	series: [
		{
			name: 'Product A',
			data: [44, 55, 41, 67, 22, 43, 21, 49]
		},
		{
			name: 'Product B',
			data: [13, 23, 20, 8, 13, 27, 33, 12]
		},
		{
			name: 'Product C',
			data: [11, 17, 15, 15, 21, 14, 15, 13]
		}
	],
	xaxis: {
		categories: [
			'2011 Q1',
			'2011 Q2',
			'2011 Q3',
			'2011 Q4',
			'2012 Q1',
			'2012 Q2',
			'2012 Q3',
			'2012 Q4'
		]
	},
	fill: {
		opacity: 1
	},
	legend: {
		offsetY: 7
	},
	colors: colors,
	grid: {
		row: {
			colors: ['transparent', 'transparent'], // takes an array which will be repeated on columns
			opacity: 0.2
		},
		borderColor: '#f1f3fa',
		padding: {
			bottom: 5
		}
	}
};

var chart = new ApexCharts(document.querySelector('#full-stacked-column'), options);

chart.render();

//
// COLUMN WITH MARKERS
//

var colors = ['#30cf46', '#fa5c7c'];
var dataColors = $('#column-with-markers').data('colors');
if (dataColors) {
	colors = dataColors.split(',');
}

var options = {
	series: [
		{
			name: 'Actual',
			data: [
				{
					x: '2011',
					y: 1292,
					goals: [
						{
							name: 'Expected',
							value: 1400,
							strokeHeight: 5,
							strokeColor: colors[1]
						}
					]
				},
				{
					x: '2012',
					y: 4432,
					goals: [
						{
							name: 'Expected',
							value: 5400,
							strokeHeight: 5,
							strokeColor: colors[1]
						}
					]
				},
				{
					x: '2013',
					y: 5423,
					goals: [
						{
							name: 'Expected',
							value: 5200,
							strokeHeight: 5,
							strokeColor: colors[1]
						}
					]
				},
				{
					x: '2014',
					y: 6653,
					goals: [
						{
							name: 'Expected',
							value: 6500,
							strokeHeight: 5,
							strokeColor: colors[1]
						}
					]
				},
				{
					x: '2015',
					y: 8133,
					goals: [
						{
							name: 'Expected',
							value: 6600,
							strokeHeight: 13,
							strokeWidth: 0,
							strokeLineCap: 'round',
							strokeColor: colors[1]
						}
					]
				},
				{
					x: '2016',
					y: 7132,
					goals: [
						{
							name: 'Expected',
							value: 7500,
							strokeHeight: 5,
							strokeColor: colors[1]
						}
					]
				},
				{
					x: '2017',
					y: 7332,
					goals: [
						{
							name: 'Expected',
							value: 8700,
							strokeHeight: 5,
							strokeColor: colors[1]
						}
					]
				},
				{
					x: '2018',
					y: 6553,
					goals: [
						{
							name: 'Expected',
							value: 7300,
							strokeHeight: 2,
							strokeDashArray: 2,
							strokeColor: colors[1]
						}
					]
				}
			]
		}
	],
	chart: {
		height: 380,
		type: 'bar'
	},
	plotOptions: {
		bar: {
			columnWidth: '60%'
		}
	},
	colors: colors,
	dataLabels: {
		enabled: false
	},
	legend: {
		show: true,
		showForSingleSeries: true,
		customLegendItems: ['Actual', 'Expected'],
		markers: {
			fillColors: colors
		}
	}
};

var chart = new ApexCharts(document.querySelector('#column-with-markers'), options);
chart.render();

//
// COLUMN WITH GROUP LABEL
//

var colors = ['#30cf46', '#fa5c7c'];
var dataColors = $('#column-with-group-label').data('colors');
if (dataColors) {
	colors = dataColors.split(',');
}

dayjs.extend(window.dayjs_plugin_quarterOfYear);
var optionsGroup = {
	series: [
		{
			name: 'Sales',
			data: [
				{
					x: '2020/01/01',
					y: 400
				},
				{
					x: '2020/04/01',
					y: 430
				},
				{
					x: '2020/07/01',
					y: 448
				},
				{
					x: '2020/10/01',
					y: 470
				},
				{
					x: '2021/01/01',
					y: 540
				},
				{
					x: '2021/04/01',
					y: 580
				},
				{
					x: '2021/07/01',
					y: 690
				},
				{
					x: '2021/10/01',
					y: 690
				}
			]
		}
	],
	chart: {
		type: 'bar',
		height: 380,
		toolbar: {
			show: false
		}
	},
	plotOptions: {
		bar: {
			horizontal: false,
			columnWidth: '45%'
		}
	},
	colors: colors,
	xaxis: {
		type: 'category',
		labels: {
			formatter: function (val) {
				return 'Q' + dayjs(val).quarter();
			}
		},
		group: {
			style: {
				fontSize: '10px',
				fontWeight: 700
			},
			groups: [
				{
					title: '2020',
					cols: 4
				},
				{
					title: '2021',
					cols: 4
				}
			]
		}
	},
	tooltip: {
		x: {
			formatter: function (val) {
				return 'Q' + dayjs(val).quarter() + ' ' + dayjs(val).format('YYYY');
			}
		}
	}
};

var chartGroup = new ApexCharts(document.querySelector('#column-with-group-label'), optionsGroup);
chartGroup.render();

//
// COLUMN CHART WITH ROTATED LABELS & ANNOTATIONS
//
var colors = ['#fa5c7c'];
var dataColors = $('#rotate-labels-column').data('colors');
if (dataColors) {
	colors = dataColors.split(',');
}
var options = {
	annotations: {
		points: [
			{
				x: 'Bananas',
				seriesIndex: 0,
				label: {
					borderColor: '#5b69bc',
					offsetY: 0,
					style: {
						color: '#fff',
						background: '#5b69bc'
					},
					text: 'Bananas are good'
				}
			}
		]
	},
	chart: {
		height: 380,
		type: 'bar',
		toolbar: {
			show: false
		}
	},
	plotOptions: {
		bar: {
			columnWidth: '50%',
			endingShape: 'rounded'
		}
	},
	dataLabels: {
		enabled: false
	},
	stroke: {
		width: 2
	},
	colors: colors,
	series: [
		{
			name: 'Servings',
			data: [44, 55, 41, 67, 22, 43, 21, 33, 45, 31, 87, 65, 35]
		}
	],
	grid: {
		borderColor: '#f1f3fa',
		padding: {
			top: 0,
			right: -2,
			bottom: -35,
			left: 10
		}
	},
	xaxis: {
		labels: {
			rotate: -45
		},
		categories: [
			'Apples',
			'Oranges',
			'Strawberries',
			'Pineapples',
			'Mangoes',
			'Bananas',
			'Blackberries',
			'Pears',
			'Watermelons',
			'Cherries',
			'Pomegranates',
			'Tangerines',
			'Papayas'
		]
	},
	yaxis: {
		title: {
			text: 'Servings'
		}
	},
	fill: {
		type: 'gradient',
		gradient: {
			shade: 'light',
			type: 'horizontal',
			shadeIntensity: 0.25,
			gradientToColors: undefined,
			inverseColors: true,
			opacityFrom: 0.85,
			opacityTo: 0.85,
			stops: [50, 0, 100]
		}
	}
};

var chart = new ApexCharts(document.querySelector('#rotate-labels-column'), options);

chart.render();

//
// COLUMN CHART WITH NEGATIVE VALUES
//
var colors = ['#5b69bc'];
var dataColors = $('#negative-value-column').data('colors');
if (dataColors) {
	colors = dataColors.split(',');
}
var options = {
	chart: {
		height: 380,
		type: 'bar',
		toolbar: {
			show: false
		}
	},
	plotOptions: {
		bar: {
			colors: {
				ranges: [
					{
						from: -100,
						to: -46,
						color: '#fa5c7c'
					},
					{
						from: -45,
						to: 0,
						color: '#faae37'
					}
				]
			},
			columnWidth: '80%'
		}
	},
	dataLabels: {
		enabled: false
	},
	colors: colors,
	series: [
		{
			name: 'Cash Flow',
			data: [
				1.45, 5.42, 5.9, -0.42, -12.6, -18.1, -18.2, -14.16, -11.1, -6.09, 0.34, 3.88, 13.07, 5.8,
				2, 7.37, 8.1, 13.57, 15.75, 17.1, 19.8, -27.03, -54.4, -47.2, -43.3, -18.6, -48.6, -41.1,
				-39.6, -37.6, -29.4, -21.4, -2.4
			]
		}
	],
	yaxis: {
		title: {
			text: 'Growth'
		},
		labels: {
			formatter: function (y) {
				return y.toFixed(0) + '%';
			}
		}
	},
	xaxis: {
		// TODO: uncomment below and fix the error
		//type: 'datetime',
		categories: [
			'2011-01-01',
			'2011-02-01',
			'2011-03-01',
			'2011-04-01',
			'2011-05-01',
			'2011-06-01',
			'2011-07-01',
			'2011-08-01',
			'2011-09-01',
			'2011-10-01',
			'2011-11-01',
			'2011-12-01',
			'2012-01-01',
			'2012-02-01',
			'2012-03-01',
			'2012-04-01',
			'2012-05-01',
			'2012-06-01',
			'2012-07-01',
			'2012-08-01',
			'2012-09-01',
			'2012-10-01',
			'2012-11-01',
			'2012-12-01',
			'2013-01-01',
			'2013-02-01',
			'2013-03-01',
			'2013-04-01',
			'2013-05-01',
			'2013-06-01',
			'2013-07-01',
			'2013-08-01',
			'2013-09-01'
		],
		labels: {
			rotate: -90
		}
	},
	grid: {
		row: {
			colors: ['transparent', 'transparent'], // takes an array which will be repeated on columns
			opacity: 0.2
		},
		borderColor: '#f1f3fa'
	}
};

var chart = new ApexCharts(document.querySelector('#negative-value-column'), options);

chart.render();

//
// DISTRIBUTED COLUMN CHART
//
var colors = [
	'#5b69bc',
	'#4bbee1',
	'#30cf46',
	'#fa5c7c',
	'#faae37',
	'#39afd1',
	'#e3eaef',
	'#313a46'
];
var dataColors = $('#distributed-column').data('colors');
if (dataColors) {
	colors = dataColors.split(',');
}
var options = {
	chart: {
		height: 380,
		type: 'bar',
		toolbar: {
			show: false
		},
		events: {
			click: function (chart, w, e) {
				console.log(chart, w, e);
			}
		}
	},
	colors: colors,
	plotOptions: {
		bar: {
			columnWidth: '45%',
			distributed: true
		}
	},
	dataLabels: {
		enabled: false
	},
	series: [
		{
			data: [21, 22, 10, 28, 16, 21, 13, 30]
		}
	],
	xaxis: {
		categories: ['John', 'Joe', 'Jake', 'Amber', 'Peter', 'Mary', 'David', 'Lily'],
		labels: {
			style: {
				colors: colors,
				fontSize: '14px'
			}
		}
	},
	legend: {
		offsetY: 7
	},
	grid: {
		row: {
			colors: ['transparent', 'transparent'], // takes an array which will be repeated on columns
			opacity: 0.2
		},
		borderColor: '#f1f3fa'
	}
};

var chart = new ApexCharts(document.querySelector('#distributed-column'), options);

chart.render();

//
// Range Column Chart
//
var colors = ['#30cf46', '#39afd1'];
var dataColors = $('#range-column').data('colors');
if (dataColors) {
	colors = dataColors.split(',');
}
var options = {
	chart: {
		height: 380,
		type: 'rangeBar'
	},
	plotOptions: {
		bar: {
			horizontal: false
		}
	},
	dataLabels: {
		enabled: true
	},
	legend: {
		offsetY: 7
	},
	colors: colors,
	series: [
		{
			name: 'Product A',
			data: [
				{
					x: 'Team A',
					y: [1, 5]
				},
				{
					x: 'Team B',
					y: [4, 6]
				},
				{
					x: 'Team C',
					y: [5, 8]
				},
				{
					x: 'Team D',
					y: [3, 11]
				}
			]
		},
		{
			name: 'Product B',
			data: [
				{
					x: 'Team A',
					y: [2, 6]
				},
				{
					x: 'Team B',
					y: [1, 3]
				},
				{
					x: 'Team C',
					y: [7, 8]
				},
				{
					x: 'Team D',
					y: [5, 9]
				}
			]
		}
	]
};

var chart = new ApexCharts(document.querySelector('#range-column'), options);

chart.render();

//
// DYNAMIC LOADED CHART
//

var colors = [
	'#5b69bc',
	'#4bbee1',
	'#30cf46',
	'#fa5c7c',
	'#faae37',
	'#39afd1',
	'#e3eaef',
	'#313a46'
];
var dataColors = $('#chart-year').data('colors');
if (dataColors) {
	colors = dataColors.split(',');
}

Apex = {
	chart: {
		toolbar: {
			show: false
		}
	},
	tooltip: {
		shared: false
	},
	legend: {
		show: false
	}
};

/**
 * Randomize array element order in-place.
 * Using Durstenfeld shuffle algorithm.
 */
function shuffleArray(array) {
	for (var i = array.length - 1; i > 0; i--) {
		var j = Math.floor(Math.random() * (i + 1));
		var temp = array[i];
		array[i] = array[j];
		array[j] = temp;
	}
	return array;
}

var arrayData = [
	{
		y: 400,
		quarters: [
			{
				x: 'Q1',
				y: 120
			},
			{
				x: 'Q2',
				y: 90
			},
			{
				x: 'Q3',
				y: 100
			},
			{
				x: 'Q4',
				y: 90
			}
		]
	},
	{
		y: 430,
		quarters: [
			{
				x: 'Q1',
				y: 120
			},
			{
				x: 'Q2',
				y: 110
			},
			{
				x: 'Q3',
				y: 90
			},
			{
				x: 'Q4',
				y: 110
			}
		]
	},
	{
		y: 448,
		quarters: [
			{
				x: 'Q1',
				y: 70
			},
			{
				x: 'Q2',
				y: 100
			},
			{
				x: 'Q3',
				y: 140
			},
			{
				x: 'Q4',
				y: 138
			}
		]
	},
	{
		y: 470,
		quarters: [
			{
				x: 'Q1',
				y: 150
			},
			{
				x: 'Q2',
				y: 60
			},
			{
				x: 'Q3',
				y: 190
			},
			{
				x: 'Q4',
				y: 70
			}
		]
	},
	{
		y: 540,
		quarters: [
			{
				x: 'Q1',
				y: 120
			},
			{
				x: 'Q2',
				y: 120
			},
			{
				x: 'Q3',
				y: 130
			},
			{
				x: 'Q4',
				y: 170
			}
		]
	},
	{
		y: 580,
		quarters: [
			{
				x: 'Q1',
				y: 170
			},
			{
				x: 'Q2',
				y: 130
			},
			{
				x: 'Q3',
				y: 120
			},
			{
				x: 'Q4',
				y: 160
			}
		]
	}
];

function makeData() {
	var dataSet = shuffleArray(arrayData);

	var dataYearSeries = [
		{
			x: '2011',
			y: dataSet[0].y,
			color: colors[0],
			quarters: dataSet[0].quarters
		},
		{
			x: '2012',
			y: dataSet[1].y,
			color: colors[1],
			quarters: dataSet[1].quarters
		},
		{
			x: '2013',
			y: dataSet[2].y,
			color: colors[2],
			quarters: dataSet[2].quarters
		},
		{
			x: '2014',
			y: dataSet[3].y,
			color: colors[3],
			quarters: dataSet[3].quarters
		},
		{
			x: '2015',
			y: dataSet[4].y,
			color: colors[4],
			quarters: dataSet[4].quarters
		},
		{
			x: '2016',
			y: dataSet[5].y,
			color: colors[5],
			quarters: dataSet[5].quarters
		}
	];

	return dataYearSeries;
}

function updateQuarterChart(sourceChart, destChartIDToUpdate) {
	var series = [];
	var seriesIndex = 0;
	var colors = [];

	if (sourceChart.w.globals.selectedDataPoints[0]) {
		var selectedPoints = sourceChart.w.globals.selectedDataPoints;
		for (var i = 0; i < selectedPoints[seriesIndex].length; i++) {
			var selectedIndex = selectedPoints[seriesIndex][i];
			var yearSeries = sourceChart.w.config.series[seriesIndex];
			series.push({
				name: yearSeries.data[selectedIndex].x,
				data: yearSeries.data[selectedIndex].quarters
			});
			colors.push(yearSeries.data[selectedIndex].color);
		}

		if (series.length === 0)
			series = [
				{
					data: []
				}
			];

		return ApexCharts.exec(destChartIDToUpdate, 'updateOptions', {
			series: series,
			colors: colors,
			fill: {
				colors: colors
			}
		});
	}
}

var options = {
	series: [
		{
			data: makeData()
		}
	],
	chart: {
		id: 'barYear',
		height: 400,
		width: '100%',
		type: 'bar',
		events: {
			dataPointSelection: function (e, chart, opts) {
				var quarterChartEl = document.querySelector('#chart-quarter');
				var yearChartEl = document.querySelector('#chart-year');

				if (opts.selectedDataPoints[0].length === 1) {
					if (quarterChartEl.classList.contains('active')) {
						updateQuarterChart(chart, 'barQuarter');
					} else {
						yearChartEl.classList.add('chart-quarter-activated');
						quarterChartEl.classList.add('active');
						updateQuarterChart(chart, 'barQuarter');
					}
				} else {
					updateQuarterChart(chart, 'barQuarter');
				}

				if (opts.selectedDataPoints[0].length === 0) {
					yearChartEl.classList.remove('chart-quarter-activated');
					quarterChartEl.classList.remove('active');
				}
			},
			updated: function (chart) {
				updateQuarterChart(chart, 'barQuarter');
			}
		}
	},
	plotOptions: {
		bar: {
			distributed: true,
			horizontal: true,
			barHeight: '75%',
			dataLabels: {
				position: 'bottom'
			}
		}
	},
	dataLabels: {
		enabled: true,
		textAnchor: 'start',
		style: {
			colors: ['#fff']
		},
		formatter: function (val, opt) {
			return opt.w.globals.labels[opt.dataPointIndex];
		},
		offsetX: 0,
		dropShadow: {
			enabled: true
		}
	},

	colors: colors,

	states: {
		normal: {
			filter: {
				type: 'desaturate'
			}
		},
		active: {
			allowMultipleDataPointsSelection: true,
			filter: {
				type: 'darken',
				value: 1
			}
		}
	},
	tooltip: {
		x: {
			show: false
		},
		y: {
			title: {
				formatter: function (val, opts) {
					return opts.w.globals.labels[opts.dataPointIndex];
				}
			}
		}
	},
	title: {
		text: 'Yearly Results',
		offsetX: 15
	},
	subtitle: {
		text: '(Click on bar to see details)',
		offsetX: 15
	},
	xaxis: {
		axisBorder: {
			show: false
		}
	},
	yaxis: {
		labels: {
			show: false
		}
	}
};

var chart = new ApexCharts(document.querySelector('#chart-year'), options);
chart.render();

var optionsQuarter = {
	series: [
		{
			data: []
		}
	],
	chart: {
		id: 'barQuarter',
		height: 400,
		width: '100%',
		type: 'bar',
		stacked: true
	},
	plotOptions: {
		bar: {
			columnWidth: '50%',
			horizontal: false
		}
	},
	legend: {
		show: false
	},
	grid: {
		yaxis: {
			lines: {
				show: false
			}
		},
		xaxis: {
			lines: {
				show: true
			}
		}
	},
	xaxis: {
		axisBorder: {
			show: false
		}
	},
	yaxis: {
		labels: {
			show: false
		}
	},
	title: {
		text: 'Quarterly Results',
		offsetX: 10
	},
	tooltip: {
		x: {
			formatter: function (val, opts) {
				return opts.w.globals.seriesNames[opts.seriesIndex];
			}
		},
		y: {
			title: {
				formatter: function (val, opts) {
					return opts.w.globals.labels[opts.dataPointIndex];
				}
			}
		}
	}
};

var chartQuarter = new ApexCharts(document.querySelector('#chart-quarter'), optionsQuarter);
chartQuarter.render();

chart.addEventListener('dataPointSelection', function (e, chart, opts) {
	var quarterChartEl = document.querySelector('#chart-quarter');
	var yearChartEl = document.querySelector('#chart-year');

	if (opts.selectedDataPoints[0].length === 1) {
		if (quarterChartEl.classList.contains('active')) {
			updateQuarterChart(chart, 'barQuarter');
		} else {
			yearChartEl.classList.add('chart-quarter-activated');
			quarterChartEl.classList.add('active');
			updateQuarterChart(chart, 'barQuarter');
		}
	} else {
		updateQuarterChart(chart, 'barQuarter');
	}

	if (opts.selectedDataPoints[0].length === 0) {
		yearChartEl.classList.remove('chart-quarter-activated');
		quarterChartEl.classList.remove('active');
	}
});

chart.addEventListener('updated', function (chart) {
	updateQuarterChart(chart, 'barQuarter');
});

document.querySelector('#model').addEventListener('change', function (e) {
	chart.updateSeries([
		{
			data: makeData()
		}
	]);
});
