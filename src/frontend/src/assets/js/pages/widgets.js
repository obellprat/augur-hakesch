
// 
// Total Orders Chart
//
var colors = ["#727cf5", "#0acf97", "#fa5c7c", "#ffbc00"];
var dataColors = $("#chart-one").data('colors');
if (dataColors) {
    colors = dataColors.split(",");
}
var options1 = {
    series: [65],
    chart: {
        type: 'radialBar',
        height: 81,
        width: 81,
        sparkline: {
            enabled: false
        }
    },
    plotOptions: {
        radialBar: {
            offsetY: 0,
            hollow: {
                margin: 0,
                size: '50%'
            },
            dataLabels: {
                name: {
                    show: false,
                },
                value: {
                    offsetY: 5,
                    fontSize: '14px',
                    fontWeight: "600",
                    formatter: function (val) {
                        return val + 'k'
                    }
                }
            }
        }
    },
    grid: {
        padding: {
            top: -18,
            bottom: -20,
            left: -20,
            right: -20,
        }
    },
    colors: colors,
}


new ApexCharts(document.querySelector("#chart-one"), options1).render();

// 
// New Users Chart
//
var colors = ["#727cf5", "#0acf97", "#fa5c7c", "#ffbc00"];
var dataColors = $("#chart-two").data('colors');
if (dataColors) {
    colors = dataColors.split(",");
}
var options2 = {
    series: [75],
    chart: {
        type: 'radialBar',
        height: 81,
        width: 81,
        sparkline: {
            enabled: false
        }
    },
    plotOptions: {
        radialBar: {
            offsetY: 0,
            hollow: {
                margin: 0,
                size: '50%'
            },
            dataLabels: {
                name: {
                    show: false,
                },
                value: {
                    offsetY: 5,
                    fontSize: '14px',
                    fontWeight: "600",
                    formatter: function (val) {
                        return val + 'k'
                    }
                }
            }
        }
    },
    grid: {
        padding: {
            top: -18,
            bottom: -20,
            left: -20,
            right: -20,
        }
    },
    colors: colors,
}


new ApexCharts(document.querySelector("#chart-two"), options2).render();


// 
// New Users Chart
//
var colors = ["#727cf5", "#0acf97", "#fa5c7c", "#ffbc00"];
var dataColors = $("#chart-three").data('colors');
if (dataColors) {
    colors = dataColors.split(",");
}
var options2 = {
    series: [75],
    chart: {
        type: 'radialBar',
        height: 81,
        width: 81,
        sparkline: {
            enabled: false
        }
    },
    plotOptions: {
        radialBar: {
            offsetY: 0,
            hollow: {
                margin: 0,
                size: '50%'
            },
            dataLabels: {
                name: {
                    show: false,
                },
                value: {
                    offsetY: 5,
                    fontSize: '14px',
                    fontWeight: "600",
                    formatter: function (val) {
                        return val + 'k'
                    }
                }
            }
        }
    },
    grid: {
        padding: {
            top: -18,
            bottom: -20,
            left: -20,
            right: -20,
        }
    },
    colors: colors,
}


new ApexCharts(document.querySelector("#chart-three"), options2).render();


// 
// New Users Chart
//
var colors = ["#727cf5", "#0acf97", "#fa5c7c", "#ffbc00"];
var dataColors = $("#chart-four").data('colors');
if (dataColors) {
    colors = dataColors.split(",");
}
var options2 = {
    series: [75],
    chart: {
        type: 'radialBar',
        height: 81,
        width: 81,
        sparkline: {
            enabled: false
        }
    },
    plotOptions: {
        radialBar: {
            offsetY: 0,
            hollow: {
                margin: 0,
                size: '50%'
            },
            dataLabels: {
                name: {
                    show: false,
                },
                value: {
                    offsetY: 5,
                    fontSize: '14px',
                    fontWeight: "600",
                    formatter: function (val) {
                        return val + 'k'
                    }
                }
            }
        }
    },
    grid: {
        padding: {
            top: -18,
            bottom: -20,
            left: -20,
            right: -20,
        }
    },
    colors: colors,
}


new ApexCharts(document.querySelector("#chart-four"), options2).render();