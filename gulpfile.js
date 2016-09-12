"use strict"

const chmod = require("gulp-chmod");
const del = require("del");
const gulp = require("gulp");
const lambda = require("gulp-awslambda");
const shell = require('gulp-shell')
const zip = require("gulp-zip");

const dest = {
    lambda: "dist"
};
const paths = {
    src: [
        "worker.py",
        "config.py",
        "deploy-worker"
    ]
};

gulp.task("clean", function () {
    return del([ dest.lambda ]);
});

gulp.task("lambda.cert", function() {
    return gulp.src(`${process.env.HOME}/.machine/{ca,key,cert}.pem`).
        pipe(chmod(644)).
        pipe(gulp.dest(`${dest.lambda}/cert`));
});

gulp.task("lambda.vendor.docker", function() {
    return gulp.src("/usr/local/bin/docker").
        pipe(gulp.dest(`${dest.lambda}/vendor`));
});

gulp.task("lambda.vendor.awscli", function() {
    return gulp.src("vendor/aws").
        pipe(gulp.dest(`${dest.lambda}/vendor`));
});

gulp.task("lambda.vendor.compose", function() {
    return gulp.src("vendor/docker-compose").
        pipe(gulp.dest(`${dest.lambda}/vendor`));
});

gulp.task("lambda.vendor", [ "lambda.vendor.docker", "lambda.vendor.awscli", "lambda.vendor.compose" ]);

gulp.task("lambda.py.src", function () {
    return gulp.src(paths.src).
        pipe(gulp.dest(dest.lambda));
});

gulp.task("lambda.py", [ "lambda.py.src" ], shell.task([
    `cd ${dest.lambda} && pip install -r ../requirements.txt -t .`
]));

gulp.task("lambda", [ "lambda.cert", "lambda.vendor", "lambda.py" ], function() {
    gulp.src([ `${dest.lambda}/**/*`, `!${dest.lambda}/app.zip` ], { dot: true }).
        pipe(zip("app.zip")).
        pipe(gulp.dest(dest.lambda));
});

gulp.task("default", [ "lambda" ]);

gulp.task("deploy", [ "lambda" ], function () {
    let FunctionName = "lambda-deploy-worker";
    gulp.src([ `${dest.lambda}/**/*`, `!${dest.lambda}/app.zip` ]).
        pipe(zip("app.zip")).
        pipe(lambda(FunctionName, { region: "ap-northeast-1" }));
});
