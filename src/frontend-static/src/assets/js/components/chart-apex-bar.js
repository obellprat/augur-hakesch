/**
 * Theme: Arclon - Responsive Bootstrap 5 Admin Dashboard
 * Author: Coderthemes
 * Module/App: Apex Bar Charts
 */

//
// BASIC BAR CHART
//

var colors = ["#39afd1"];
var dataColors = $("#basic-bar").data('colors');
if (dataColors) {
    colors = dataColors.split(",");
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
            horizontal: true,
        }
    },
    dataLabels: {
        enabled: false
    },
    series: [{
        data: [400, 430, 448, 470, 540, 580, 690, 1100, 1200, 1380]
    }],
    colors: colors,
    xaxis: {
        categories: ['South Korea', 'Canada', 'United Kingdom', 'Netherlands', 'Italy', 'France', 'Japan', 'United States', 'China', 'Germany'],
        axisBorder: {
            show: false,
        }
    },
    states: {
        hover: {
            filter: 'none'
        }
    },
    grid: {
        borderColor: '#f1f3fa'
    }
}

var chart = new ApexCharts(
    document.querySelector("#basic-bar"),
    options
);

chart.render();


//
// GROUPED BAR CHART
//
var colors = ["#fa5c7c", "#4bbee1"];
var dataColors = $("#grouped-bar").data('colors');
if (dataColors) {
    colors = dataColors.split(",");
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
            horizontal: true,
            dataLabels: {
                position: 'top',
            },
        }
    },
    dataLabels: {
        enabled: true,
        offsetX: -6,
        style: {
            fontSize: '12px',
            colors: ['#fff']
        }
    },
    colors: colors,
    stroke: {
        show: true,
        width: 1,
        colors: ['transparent']
    },
    series: [{
        name: 'Series 1',
        data: [44, 55, 41, 64, 22, 43, 21]
    }, {
        name: 'Series 2',
        data: [53, 32, 33, 52, 13, 44, 32]
    }],
    xaxis: {
        categories: [2001, 2002, 2003, 2004, 2005, 2006, 2007],
        axisBorder: {
            show: false,
        }
    },
    legend: {
        offsetY: 5,
    },
    states: {
        hover: {
            filter: 'none'
        }
    },
    grid: {
        borderColor: '#f1f3fa',
        padding: {
            bottom: 5
        }
    }
}

var chart = new ApexCharts(
    document.querySelector("#grouped-bar"),
    options
);

chart.render();


//
// STACKED BAR CHART
//
var colors = ["#5b69bc", "#30cf46", "#fa5c7c", "#4bbee1", "#39afd1"];
var dataColors = $("#stacked-bar").data('colors');
if (dataColors) {
    colors = dataColors.split(",");
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
            horizontal: true,
        },

    },
    stroke: {
        show: false
    },
    series: [{
        name: 'Marine Sprite',
        data: [44, 55, 41, 37, 22, 43, 21]
    }, {
        name: 'Striking Calf',
        data: [53, 32, 33, 52, 13, 43, 32]
    }, {
        name: 'Tank Picture',
        data: [12, 17, 11, 9, 15, 11, 20]
    }, {
        name: 'Bucket Slope',
        data: [9, 7, 5, 8, 6, 9, 4]
    }, {
        name: 'Reborn Kid',
        data: [25, 12, 19, 32, 25, 24, 10]
    }],
    xaxis: {
        categories: [2008, 2009, 2010, 2011, 2012, 2013, 2014],
        labels: {
            formatter: function (val) {
                return val + "K"
            }
        },
        axisBorder: {
            show: false,
        }
    },
    yaxis: {
        title: {
            text: undefined
        },

    },
    colors: colors,
    tooltip: {
        y: {
            formatter: function (val) {
                return val + "K"
            }
        }
    },
    fill: {
        opacity: 1
    },
    states: {
        hover: {
            filter: 'none'
        }
    },
    legend: {
        position: 'top',
        horizontalAlign: 'center',
        offsetY: 10
    },
    grid: {
        borderColor: '#f1f3fa'
    }
}

var chart = new ApexCharts(
    document.querySelector("#stacked-bar"),
    options
);

chart.render();


//
// 100% STACKED BAR CHART
//
var colors = ["#faae37", "#39afd1", "#4bbee1", "#e3eaef", "#5b69bc"];
var dataColors = $("#full-stacked-bar").data('colors');
if (dataColors) {
    colors = dataColors.split(",");
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
            horizontal: true,
        },
    },
    stroke: {
        width: 1,
        colors: ['transparent']
    },
    series: [{
        name: 'Marine Sprite',
        data: [44, 55, 41, 37, 22, 43, 21]
    }, {
        name: 'Striking Calf',
        data: [53, 32, 33, 52, 13, 43, 32]
    }, {
        name: 'Tank Picture',
        data: [12, 17, 11, 9, 15, 11, 20]
    }, {
        name: 'Bucket Slope',
        data: [9, 7, 5, 8, 6, 9, 4]
    }, {
        name: 'Reborn Kid',
        data: [25, 12, 19, 32, 25, 24, 10]
    }],
    xaxis: {
        categories: [2008, 2009, 2010, 2011, 2012, 2013, 2014],
        axisBorder: {
            show: false,
        }
    },
    colors: colors,
    tooltip: {
        y: {
            formatter: function (val) {
                return val + "K"
            }
        }
    },
    fill: {
        opacity: 1

    },
    states: {
        hover: {
            filter: 'none'
        }
    },
    legend: {
        position: 'top',
        horizontalAlign: 'center',
        offsetY: 10
    },
    grid: {
        borderColor: '#f1f3fa',
        padding: {
            top: 0
        }
    }
}

var chart = new ApexCharts(
    document.querySelector("#full-stacked-bar"),
    options
);

chart.render();


//
// BAR WITH NEGATIVE VALUES
//
var colors = ["#fa5c7c", "#30cf46"];
var dataColors = $("#negative-bar").data('colors');
if (dataColors) {
    colors = dataColors.split(",");
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
    colors: colors,
    plotOptions: {
        bar: {
            horizontal: true,
            barHeight: '80%',
        },
    },
    dataLabels: {
        enabled: false
    },
    stroke: {
        width: 1,
        colors: ["transparent"]
    },
    series: [{
        name: 'Males',
        data: [0.4, 0.65, 0.76, 0.88, 1.5, 2.1, 2.9, 3.8, 3.9, 4.2, 4, 4.3, 4.1, 4.2, 4.5, 3.9, 3.5, 3]
    },
    {
        name: 'Females',
        data: [-0.8, -1.05, -1.06, -1.18, -1.4, -2.2, -2.85, -3.7, -3.96, -4.22, -4.3, -4.4, -4.1, -4, -4.1, -3.4, -3.1, -2.8]
    }],
    grid: {
        xaxis: {
            showLines: false,
        }
    },
    yaxis: {
        min: -5,
        max: 5,
        title: {
            // text: 'Age',
        },
    },
    tooltip: {
        shared: false,
        x: {
            formatter: function (val) {
                return val
            }
        },
        y: {
            formatter: function (val) {
                return Math.abs(val) + "%"
            }
        }
    },
    xaxis: {
        categories: ['85+', '80-84', '75-79', '70-74', '65-69', '60-64', '55-59', '50-54', '45-49', '40-44', '35-39', '30-34', '25-29', '20-24', '15-19', '10-14', '5-9', '0-4'],
        title: {
            text: 'Percent'
        },
        labels: {
            formatter: function (val) {
                return Math.abs(Math.round(val)) + "%"
            }
        },
        axisBorder: {
            show: false,
        }
    },
    legend: {
        offsetY: 7,
    },
    grid: {
        borderColor: '#f1f3fa',
        padding: {
            bottom: 5
        }
    }
}

var chart = new ApexCharts(
    document.querySelector("#negative-bar"),
    options
);

chart.render();


// 
// Reversed Bar Chart
//

var dataColors = $("#reversed-bar").data('colors');
if (dataColors) {
    colors = dataColors.split(",");
}

var options = {
    series: [{
        data: [400, 430, 448, 470, 540, 580, 690]
    }],
    chart: {
        type: 'bar',
        height: 380
    },
    annotations: {
        xaxis: [{
            x: 500,
            borderColor: colors[1],
            label: {
                borderColor: colors[1],
                style: {
                    color: '#fff',
                    background: colors[1],
                },
                text: 'X annotation',
            }
        }],
        yaxis: [{
            y: 'July',
            y2: 'September',
            label: {
                text: 'Y annotation'
            }
        }]
    },
    plotOptions: {
        bar: {
            horizontal: true,
        }
    },
    dataLabels: {
        enabled: true
    },
    xaxis: {
        categories: ['June', 'July', 'August', 'September', 'October', 'November', 'December'],
        axisBorder: {
            show: false,
        }
    },
    colors: colors,
    grid: {
        xaxis: {
            lines: {
                show: true
            }
        }
    },
    yaxis: {
        reversed: true,
        axisTicks: {
            show: true
        }
    }
};

var chart = new ApexCharts(document.querySelector("#reversed-bar"), options);
chart.render();


//
// PATTERNED BAR CHART
//
var colors = ["#5b69bc", "#30cf46", "#fa5c7c", "#39afd1"];
var dataColors = $("#pattern-bar").data('colors');
if (dataColors) {
    colors = dataColors.split(",");
}
var options = {
    chart: {
        height: 380,
        type: 'bar',
        stacked: true,
        toolbar: {
            show: false
        },
        shadow: {
            enabled: true,
            blur: 1,
            opacity: 0.5
        }
    },
    plotOptions: {
        bar: {
            horizontal: true,
            barHeight: '60%',

        },
    },
    dataLabels: {
        enabled: false
    },
    stroke: {
        width: 2,
    },
    series: [{
        name: 'Marine Sprite',
        data: [44, 55, 41, 37, 22, 43, 21]
    }, {
        name: 'Striking Calf',
        data: [53, 32, 33, 52, 13, 43, 32]
    }, {
        name: 'Tank Picture',
        data: [12, 17, 11, 9, 15, 11, 20]
    }, {
        name: 'Bucket Slope',
        data: [9, 7, 5, 8, 6, 9, 4]
    }],
    xaxis: {
        categories: [2008, 2009, 2010, 2011, 2012, 2013, 2014],
        axisBorder: {
            show: false,
        }
    },
    yaxis: {
        title: {
            text: undefined
        },
    },
    tooltip: {
        shared: false,
        y: {
            formatter: function (val) {
                return val + "K"
            }
        }
    },
    colors: colors,
    fill: {
        type: 'pattern',
        opacity: 1,
        pattern: {
            style: ['circles', 'slantedLines', 'verticalLines', 'horizontalLines'], // string or array of strings

        }
    },
    states: {
        hover: {
            filter: 'none'
        }
    },
    legend: {
        position: 'right',
    },
    grid: {
        borderColor: '#f1f3fa'
    },
    responsive: [{
        breakpoint: 600,
        options: {
            legend: {
                show: false
            },
        }
    }]
}

var chart = new ApexCharts(
    document.querySelector("#pattern-bar"),
    options
);

chart.render();



//
// BAR WITH IMAGE FILL
//

var labels = Array.apply(null, { length: 39 }).map(function (el, index) {
    return index + 1;
});

var options = {
    chart: {
        height: 450,
        type: 'bar',
        toolbar: {
            show: false
        },
        animations: {
            enabled: false
        }
    },
    plotOptions: {
        bar: {
            horizontal: true,
            barHeight: '100%',

        },
    },
    dataLabels: {
        enabled: false,
    },
    stroke: {
        colors: ["#fff"],
        width: 0.2
    },
    series: [{
        name: 'coins',
        data: [2, 4, 3, 4, 3, 5, 5, 6.5, 6, 5, 4, 5, 8, 7, 7, 8, 8, 10, 9, 9, 12, 12, 11, 12, 13, 14, 16, 14, 15, 17, 19, 21]
    }],
    labels: labels,
    yaxis: {
        axisBorder: {
            show: false
        },
        axisTicks: {
            show: false
        },
        labels: {
            show: false
        },
        title: {
            text: 'Weight',
        },
    },
    xaxis: {
        axisBorder: {
            show: false,
        }
    },
    grid: {
        position: 'back',
        borderColor: '#f1f3fa'
    },
    fill: {
        type: 'image',
        opacity: 0.87,
        image: {
            src: ['assets/images/small/small-4.jpg'],
            width: 466,
            height: 406
        }
    },
}

var chart = new ApexCharts(
    document.querySelector("#image-fill-bar"),
    options
);

chart.render();


// 
// CUSTOM DATALABELS BAR
//

var colors = ["#5b69bc", "#30cf46", "#fa5c7c", "#4bbee1", "#39afd1", '#2b908f', '#faae37', '#90ee7e', '#f48024', '#212730'];
var dataColors = $("#datalables-bar").data('colors');
if (dataColors) {
    colors = dataColors.split(",");
}
var options = {
    chart: {
        height: 450,
        type: 'bar'
    },
    plotOptions: {
        bar: {
            barHeight: '100%',
            distributed: true,
            horizontal: true,
            dataLabels: {
                position: 'bottom'
            },
        }
    },
    colors: colors,
    dataLabels: {
        enabled: true,
        textAnchor: 'start',
        style: {
            colors: ['#fff']
        },
        formatter: function (val, opt) {
            return opt.w.globals.labels[opt.dataPointIndex] + ":  " + val
        },
        offsetX: 0,
        dropShadow: {
            enabled: false
        }
    },
    series: [{
        data: [400, 430, 448, 470, 540, 580, 690, 1100, 1200, 1380]
    }],
    stroke: {
        width: 0,
        colors: ['#fff']
    },
    xaxis: {
        categories: ['South Korea', 'Canada', 'United Kingdom', 'Netherlands', 'Italy', 'France', 'Japan', 'United States', 'China', 'India'],
        axisBorder: {
            show: false,
        }
    },
    yaxis: {
        labels: {
            show: false
        }
    },
    grid: {
        borderColor: '#f1f3fa'
    },

    tooltip: {
        theme: 'dark',
        x: {
            show: false
        },
        y: {
            title: {
                formatter: function () {
                    return ''
                }
            }
        }
    }
}

var chart = new ApexCharts(
    document.querySelector("#datalables-bar"),
    options
);

chart.render();


// 
// Bar with Markers
//

var dataColors = $("#bar-markers").data('colors');
if (dataColors) {
    colors = dataColors.split(",");
}

var options = {
    series: [
        {
            name: 'Actual',
            data: [
                {
                    x: '2017',
                    y: 12,
                    goals: [
                        {
                            name: 'Expected',
                            value: 14,
                            strokeWidth: 2,
                            strokeDashArray: 2,
                            strokeColor: colors[1]
                        }
                    ]
                },
                {
                    x: '2018',
                    y: 44,
                    goals: [
                        {
                            name: 'Expected',
                            value: 54,
                            strokeWidth: 5,
                            strokeHeight: 10,
                            strokeColor: colors[1]
                        }
                    ]
                },
                {
                    x: '2019',
                    y: 54,
                    goals: [
                        {
                            name: 'Expected',
                            value: 52,
                            strokeWidth: 10,
                            strokeHeight: 0,
                            strokeLineCap: 'round',
                            strokeColor: colors[1]
                        }
                    ]
                },
                {
                    x: '2020',
                    y: 66,
                    goals: [
                        {
                            name: 'Expected',
                            value: 61,
                            strokeWidth: 10,
                            strokeHeight: 0,
                            strokeLineCap: 'round',
                            strokeColor: colors[1]
                        }
                    ]
                },
                {
                    x: '2021',
                    y: 81,
                    goals: [
                        {
                            name: 'Expected',
                            value: 66,
                            strokeWidth: 10,
                            strokeHeight: 0,
                            strokeLineCap: 'round',
                            strokeColor: colors[1]
                        }
                    ]
                },
                {
                    x: '2022',
                    y: 67,
                    goals: [
                        {
                            name: 'Expected',
                            value: 70,
                            strokeWidth: 5,
                            strokeHeight: 10,
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
            horizontal: true,
        }
    },
    colors: colors,
    dataLabels: {
        dataLabels: {
            formatter: function (val, opt) {
                var goals =
                    opt.w.config.series[opt.seriesIndex].data[opt.dataPointIndex]
                        .goals

                // if (goals && goals.length) {
                //   return `${val} / ${goals[0].value}`
                // }
                return val
            }
        },
    },
    legend: {
        show: true,
        showForSingleSeries: true,
        customLegendItems: ['Actual', 'Expected'],
        markers: {
            fillColors: colors
        }
    },
    xaxis: {
        axisBorder: {
            show: false,
        }
    }
};

var chart = new ApexCharts(document.querySelector("#bar-markers"), options);
chart.render();




//
//  Animation
//

// var trigoStrength = 3;
// var iteration = 11;

// function getRandom() {
//     var i = iteration;
//     return (
//         (Math.sin(i / trigoStrength) * (i / trigoStrength) +
//             i / trigoStrength +
//             1) *
//         (trigoStrength * 2)
//     );
// }

// function generateMinuteWiseTimeSeries(baseval, count, yrange) {
//     var i = 0;
//     var series = [];
//     while (i < count) {
//         var x = baseval;
//         var y =
//             (Math.sin(i / trigoStrength) * (i / trigoStrength) +
//                 i / trigoStrength +
//                 1) *
//             (trigoStrength * 2);

//         series.push([x, y]);
//         baseval += 300000;
//         i++;
//     }
//     return series;
// }
// var optionsColumn = {
//     chart: {
//         height: 350,
//         type: "bar",
//         animations: {
//             enabled: true,
//             easing: "linear",
//             dynamicAnimation: {
//                 speed: 1000
//             }
//         },
//         events: {
//             animationEnd: function (chartCtx) {
//                 const newData = chartCtx.w.config.series[0].data.slice();
//                 newData.shift();
//                 window.setTimeout(function () {
//                     chartCtx.updateOptions(
//                         {
//                             series: [
//                                 {
//                                     name: "Load Average",
//                                     data: newData
//                                 }
//                             ],
//                             xaxis: {
//                                 min: chartCtx.minX,
//                                 max: chartCtx.maxX
//                             },
//                             subtitle: {
//                                 text:
//                                     parseInt(getRangeRandom({ min: 1, max: 20 })).toString() + "%"
//                             }
//                         },
//                         false,
//                         false
//                     );
//                 }, 300);
//             }
//         },
//         toolbar: {
//             show: false
//         },
//         zoom: {
//             enabled: false
//         }
//     },
//     dataLabels: {
//         enabled: false
//     },
//     stroke: {
//         width: 0
//     },
//     colors: ['#00acf0'],
//     series: [
//         {
//             name: "Load Average",
//             data: generateMinuteWiseTimeSeries(
//                 new Date("12/12/2016 00:20:00").getTime(),
//                 12,
//                 {
//                     min: 10,
//                     max: 110
//                 }
//             )
//         }
//     ],
//     title: {
//         text: "Load Average",
//         align: "left",
//         style: {
//             fontSize: "12px"
//         }
//     },
//     subtitle: {
//         text: "20%",
//         floating: true,
//         align: "right",
//         offsetY: 0,
//         style: {
//             fontSize: "22px"
//         }
//     },
//     fill: {
//         type: "gradient",
//         gradient: {
//             shade: "dark",
//             type: "vertical",
//             shadeIntensity: 0.5,
//             inverseColors: false,
//             opacityFrom: 1,
//             opacityTo: 0.6,
//             stops: [0, 100]
//         }
//     },
//     xaxis: {
//         type: "datetime",
//         range: 2700000
//     },
//     legend: {
//         show: true
//     }
// };
// var chartColumn = new ApexCharts(
//     document.querySelector("#basic-bar"),
//     optionsColumn
// );
// chartColumn.render();
// window.setInterval(function () {
//     iteration++;
//     chartColumn.updateSeries([
//         {
//             name: "Load Average",
//             data: [
//                 ...chartColumn.w.config.series[0].data,
//                 [chartColumn.w.globals.maxX + 210000, getRandom()]
//             ]
//         }
//     ]);
// }, 2500);
// var ts2 = 1484418600000;
// var dates = [];
// var spikes = [5, -5, 3, -3, 8, -8]
// for (var i = 0; i < 120; i++) {
//     ts2 = ts2 + 86400000;
//     var innerArr = [ts2, dataSeries[1][i].value];
//     dates.push(innerArr)
// }