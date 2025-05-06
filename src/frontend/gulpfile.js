const { series, src, dest, parallel, watch } = require("gulp");

const autoprefixer = require("gulp-autoprefixer");
const babel = require('gulp-babel');
const browsersync = require("browser-sync");
const concat = require("gulp-concat");
const CleanCSS = require("gulp-clean-css");
const del = require("del");
const fileinclude = require("gulp-file-include");
//const imagemin = require("gulp-imagemin");
const npmdist = require("gulp-npm-dist");
const newer = require("gulp-newer");
const rename = require("gulp-rename");
const rtlcss = require("gulp-rtlcss");
const sourcemaps = require("gulp-sourcemaps");
const sass = require("gulp-sass")(require("sass"));
const uglify = require("gulp-uglify");
//var ts = require("gulp-typescript");
//var tsProject = ts.createProject("tsconfig.json");
var browserify = require("browserify");
var source = require("vinyl-source-stream");
var tsify = require("tsify");
var esmify = require('esmify');


const paths = {
    baseSrc: "src/",                // source directory
    baseDist: "dist/",              // build directory
    baseDistAssets: "dist/assets/", // build assets directory
    baseSrcAssets: "src/assets/",   // source assets directory
};

const clean = function (done) {
    del.sync(paths.baseDist, done());
};

const olCss = function() {
    const out = paths.baseDistAssets + "vendor/ol/";
    return src(['./node_modules/ol/ol.css'])
    .pipe(dest(out));
}

const vendor = function () {
    const out = paths.baseDistAssets + "vendor/";
    return src(npmdist(), { base: "./node_modules" })
        .pipe(rename(function (path) {
            path.dirname = path.dirname.replace(/\/dist/, '').replace(/\\dist/, '');
        }))
        .pipe(dest(out));
};

const plugin = function () {
    const outCSS = paths.baseDistAssets + "css/";

    // vendor.min.css
    src([
        // Form Advance Plugin
        paths.baseDistAssets + "vendor/flatpickr/flatpickr.min.css",
        paths.baseDistAssets + "vendor/select2/css/select2.min.css",
        paths.baseDistAssets + "vendor/choices.js/public/assets/styles/choices.min.css",
        paths.baseDistAssets + "vendor/ol/ol.css",

    ])
        .pipe(concat("vendor.css"))
        .pipe(CleanCSS())
        .pipe(rename({ suffix: ".min" }))
        .pipe(dest(outCSS));

    const outjs = paths.baseDistAssets + "js/";

    // vendor.min.js
    return src([
        paths.baseDistAssets + "vendor/jquery/jquery.min.js",
        paths.baseDistAssets + "vendor/bootstrap/js/bootstrap.bundle.min.js",
        paths.baseDistAssets + "vendor/iconify-icon/iconify-icon.min.js",
        paths.baseDistAssets + "vendor/waypoints/lib/jquery.waypoints.min.js",
        paths.baseDistAssets + "vendor/jquery.counterup/jquery.counterup.min.js",
        paths.baseDistAssets + "vendor/simplebar/simplebar.min.js",
        paths.baseDistAssets + "vendor/leaflet-geosearch/bundle.min.js",
        


        // Form Advance Plugin
        paths.baseDistAssets + "vendor/flatpickr/flatpickr.min.js",  // Flatpickr
        paths.baseDistAssets + "vendor/select2/js/select2.min.js",   // select2
        paths.baseDistAssets + "vendor/inputmask/inputmask.min.js",  // inputmask
        paths.baseDistAssets + "vendor/choices.js/public/assets/scripts/choices.min.js", // choices js
    ])
        .pipe(concat("vendor.js"))
        .pipe(uglify())
        .pipe(rename({ suffix: ".min" }))
        .pipe(dest(outjs));
};


const html = function () {
    const srcPath = paths.baseSrc + "/";
    const out = paths.baseDist;
    return src([
        srcPath + "*.html",
        srcPath + "*.ico", // favicon
        srcPath + "*.png",
    ])
        .pipe(
            fileinclude({
                prefix: "@@",
                basepath: "@file",
                indent: true,
            })
        )
        .pipe(dest(out));
};

const data = function () {
    const out = paths.baseDistAssets + "data/";
    return src([paths.baseSrcAssets + "data/**/*"])
        .pipe(dest(out));
};

const fonts = function () {
    const out = paths.baseDistAssets + "fonts/";
    return src([paths.baseSrcAssets + "fonts/**/*"])
        .pipe(newer(out))
        .pipe(dest(out));
};

const images = function () {
    var out = paths.baseDistAssets + "images";
    return src(paths.baseSrcAssets + "images/**/*")
        // .pipe(newer(out))
        // .pipe(imagemin())
        .pipe(dest(out));
};

const javascript = function () {
    const out = paths.baseDistAssets + "js/";


    // copying and minifying all other js
    return src(paths.baseSrcAssets + "js/**/*.js")
        .pipe(uglify())
        // .pipe(rename({ suffix: ".min" }))
        .pipe(dest(out));

};

const browserifyTools = function() {
    
    const out = paths.baseDistAssets + "js/";

    return browserify({
        
      insertGlobals: true,
        basedir: ".",
        debug: true,
        entries: ["src/assets/js/tools/isozones.js"],
        cache: {},
        packageCache: {},
        plugin: [ esmify ]
      })
        .bundle()
        .pipe(source("bundle.js"))
        .pipe(dest(out));

}

const scss = function () {
    const out = paths.baseDistAssets + "css/";

    src([paths.baseSrcAssets + "scss/**/*.scss", "!" + paths.baseSrcAssets + "scss/icons.scss", "!" + paths.baseSrcAssets + "scss/icons/*.scss"])
        .pipe(sourcemaps.init())
        .pipe(sass.sync().on('error', sass.logError)) // scss to css
        .pipe(
            autoprefixer({
                overrideBrowserslist: ["last 2 versions"],
            })
        )
        .pipe(dest(out))
        .pipe(CleanCSS())
        .pipe(rename({ suffix: ".min" }))
        .pipe(sourcemaps.write("./")) // source maps
        .pipe(dest(out));

    // generate rtl
    return src([paths.baseSrcAssets + "scss/**/*.scss", "!" + paths.baseSrcAssets + "scss/icons.scss", "!" + paths.baseSrcAssets + "scss/icons/*.scss"])
        .pipe(sourcemaps.init())
        .pipe(sass.sync().on('error', sass.logError)) // scss to css
        .pipe(
            autoprefixer({
                overrideBrowserslist: ["last 2 versions"],
            })
        )
        .pipe(rtlcss())
        .pipe(rename({ suffix: "-rtl" }))
        .pipe(dest(out))
        .pipe(CleanCSS())
        .pipe(rename({ suffix: ".min" }))
        .pipe(sourcemaps.write("./")) // source maps
        .pipe(dest(out));
};

const icons = function () {
    const out = paths.baseDistAssets + "css/";
    return src([paths.baseSrcAssets + "scss/icons.scss", paths.baseSrcAssets + "scss/icons/*.scss"])
        .pipe(sourcemaps.init())
        .pipe(sass.sync()) // scss to css
        .pipe(
            autoprefixer({
                overrideBrowserslist: ["last 2 versions"],
            })
        )
        .pipe(dest(out))
        .pipe(CleanCSS())
        .pipe(rename({ suffix: ".min" }))
        .pipe(sourcemaps.write("./")) // source maps
        .pipe(dest(out));
};


// live browser loading
const initBrowserSync = function (done) {
    const startPath = "/index.html";
    browsersync.init({
        startPath: startPath,
        server: {
            baseDir: paths.baseDist,
            middleware: [
                function (req, res, next) {
                    req.method = "GET";
                    next();
                },
            ],
        },
    });
    done();
}

const reloadBrowserSync = function (done) {
    browsersync.reload();
    done();
}

function watchFiles() {
    watch(paths.baseSrc + "**/*.html", series(html, copyToAPI, reloadBrowserSync));
    watch(paths.baseSrcAssets + "data/**/*", series(data, copyToAPI, reloadBrowserSync));
    watch(paths.baseSrcAssets + "fonts/**/*", series(fonts, copyToAPI, reloadBrowserSync));
    watch(paths.baseSrcAssets + "images/**/*", series(images, copyToAPI, reloadBrowserSync));
    watch(paths.baseSrcAssets + "js/**/*", series(javascript, copyToAPI, reloadBrowserSync));
    watch(paths.baseSrcAssets + "js/**/*", series(browserifyTools, copyToAPI, reloadBrowserSync));
    watch(paths.baseSrcAssets + "scss/icons.scss", series(icons, copyToAPI, reloadBrowserSync));
    watch([paths.baseSrcAssets + "scss/**/*.scss", "!" + paths.baseSrcAssets + "scss/icons.scss", "!" + paths.baseSrcAssets + "scss/icons/*.scss"], series(scss, copyToAPI, reloadBrowserSync));
}

function copyToAPI() {
    return src(['dist/**/*']).pipe(dest('../api'));
}

// Production Tasks
exports.default = series(
    html, olCss,
    vendor,
    parallel(plugin, data, fonts, images, javascript, scss, icons,browserifyTools),
    parallel(watchFiles, initBrowserSync),
    copyToAPI
);

// Build Tasks
exports.build = series(
    clean,
    html,olCss,
    vendor,
    parallel(plugin, data, fonts, images, javascript, scss, icons,browserifyTools),
    copyToAPI
);