

var colors = ["#777edd", "#0acf97", "#fa5c7c"];
var dataColors = $("#slope-basic").data('colors');
if (dataColors) {
    colors = dataColors.split(",");
}
var options = {
    series: [
        {
            name: 'Blue',
            data: [
                {
                    x: 'Jan',
                    y: 43,
                },
                {
                    x: 'Feb',
                    y: 58,
                },
            ],
        },
        {
            name: 'Green',
            data: [
                {
                    x: 'Jan',
                    y: 33,
                },
                {
                    x: 'Feb',
                    y: 38,
                },
            ],
        },
        {
            name: 'Red',
            data: [
                {
                    x: 'Jan',
                    y: 55,
                },
                {
                    x: 'Feb',
                    y: 21,
                },
            ],
        },
    ],
    colors: colors,
    chart: {
        height: 350,
        width: 400,
        type: 'line',
    },
    plotOptions: {
        line: {
            isSlopeChart: true,
        },
    }
};

var chart = new ApexCharts(document.querySelector("#slope-basic"), options);
chart.render();

// 


var colors = ["#777edd", "#0acf97", "#fd7e14", "#fa5c7c"];
var dataColors = $("#slope-mluti-group").data('colors');
if (dataColors) {
    colors = dataColors.split(",");
}
var options = {
    series: [
        {
            name: 'Blue',
            data: [
                {
                    x: 'Category 1',
                    y: 503,
                },
                {
                    x: 'Category 2',
                    y: 580,
                },
                {
                    x: 'Category 3',
                    y: 135,
                },
            ],
        },
        {
            name: 'Green',
            data: [
                {
                    x: 'Category 1',
                    y: 733,
                },
                {
                    x: 'Category 2',
                    y: 385,
                },
                {
                    x: 'Category 3',
                    y: 715,
                },
            ],
        },
        {
            name: 'Orange',
            data: [
                {
                    x: 'Category 1',
                    y: 255,
                },
                {
                    x: 'Category 2',
                    y: 211,
                },
                {
                    x: 'Category 3',
                    y: 441,
                },
            ],
        },
        {
            name: 'Red',
            data: [
                {
                    x: 'Category 1',
                    y: 428,
                },
                {
                    x: 'Category 2',
                    y: 749,
                },
                {
                    x: 'Category 3',
                    y: 559,
                },
            ],
        },
    ],
    chart: {
        height: 350,
        width: 600,
        type: 'line',
    },
    plotOptions: {
        line: {
            isSlopeChart: true,
        },
    },
    tooltip: {
        followCursor: true,
        intersect: false,
        shared: true,
    },
    dataLabels: {
        background: {
            enabled: true,
        },
        formatter(val, opts) {
            const seriesName = opts.w.config.series[opts.seriesIndex].name
            return val !== null ? seriesName : ''
        },
    },
    colors: colors,
    yaxis: {
        show: true,
        labels: {
            show: true,
        },
    },
    xaxis: {
        position: 'bottom',
    },
    legend: {
        show: true,
        position: 'top',
        horizontalAlign: 'left',
    },
    stroke: {
        width: [2, 3, 4, 2],
        dashArray: [0, 0, 5, 2],
        curve: 'smooth',
    }
};

var chart = new ApexCharts(document.querySelector("#slope-mluti-group"), options);
chart.render();