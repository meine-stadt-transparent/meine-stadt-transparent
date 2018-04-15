// https://dezoito.github.io/2016/01/06/django-automate-browsersync.html
// Extremly useful when experimenting with templates

var gulp        = require('gulp');
var browserSync = require('browser-sync');
var reload      = browserSync.reload;

gulp.task('default', function() {
    browserSync.init({
        proxy: "localhost:8000"
    });
    gulp.watch(['./**/*.{html,py,css}', 'mainapp/assets/bundles/*.js'], reload);
});

