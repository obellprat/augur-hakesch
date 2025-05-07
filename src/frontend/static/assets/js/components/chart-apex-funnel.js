/**
 * Theme: Arclon - Responsive Bootstrap 5 Admin Dashboard
 * Author: Coderthemes
 * Module/App: Apex funnel Charts
 */



// Funnel Chart

var colors = ["#777edd", "#0acf97", "#fd7e14", "#fa5c7c"];
var dataColors = $("#slope-mluti-group").data('colors');
if (dataColors) {
    colors = dataColors.split(",");
}
var options = {
    series: [
        {
            name: "Funnel Series",
            data: [1380, 1100, 990, 880, 740, 548, 330, 200],
        },
    ],
    chart: {
        type: 'bar',
        height: 350,
        dropShadow: {
            enabled: true,
        },
        toolbar: {
            show: false
        }
    },
    plotOptions: {
        bar: {
            borderRadius: 0,
            horizontal: true,
            barHeight: '80%',
            isFunnel: true,
        },
    },
    colors: colors,
    dataLabels: {
        enabled: true,
        formatter: function (val, opt) {
            return opt.w.globals.labels[opt.dataPointIndex] + ':  ' + val
        },
        dropShadow: {
            enabled: true,
        },
    },
    title: {
        text: 'Recruitment Funnel',
        align: 'middle',
    },
    xaxis: {
        categories: [
            'Sourced',
            'Screened',
            'Assessed',
            'HR Interview',
            'Technical',
            'Verify',
            'Offered',
            'Hired',
        ],
    },
    legend: {
        show: false,
    },
};

var chart = new ApexCharts(document.querySelector("#funnel-chart"), options);
chart.render();



// Pyramid Chart

var colors = ["#777edd", "#0acf97", "#fd7e14", "#fa5c7c"];
var dataColors = $("#pyramid-chart").data('colors');
if (dataColors) {
    colors = dataColors.split(",");
}
var options = {
    series: [
        {
            name: "",
            data: [200, 330, 548, 740, 880, 990, 1100, 1380],
        },
    ],
    chart: {
        type: 'bar',
        height: 350,
        dropShadow: {
            enabled: true,
        },
        toolbar: {
            show: false
        }
    },
    colors: colors,
    plotOptions: {
        bar: {
            borderRadius: 0,
            horizontal: true,
            distributed: true,
            barHeight: '80%',
            isFunnel: true,
        },
    },
    colors: [
        '#F44F5E',
        '#E55A89',
        '#D863B1',
        '#CA6CD8',
        '#B57BED',
        '#8D95EB',
        '#62ACEA',
        '#4BC3E6',
    ],
    dataLabels: {
        enabled: true,
        formatter: function (val, opt) {
            return opt.w.globals.labels[opt.dataPointIndex]
        },
        dropShadow: {
            enabled: true,
        },
    },
    title: {
        text: 'Pyramid Chart',
        align: 'middle',
    },
    xaxis: {
        categories: ['Sweets', 'Processed Foods', 'Healthy Fats', 'Meat', 'Beans & Legumes', 'Dairy', 'Fruits & Vegetables', 'Grains'],
    },
    legend: {
        show: false,
    },
};

var chart = new ApexCharts(document.querySelector("#pyramid-chart"), options);
chart.render();