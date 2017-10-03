const path = require('path');
const webpack = require('webpack');
const BundleTracker = require('webpack-bundle-tracker');
const ExtractTextPlugin = require("extract-text-webpack-plugin");

module.exports = {
    context: path.resolve(__dirname),
    entry: {
        mainapp: '../mainapp/assets/js/index',
        persons: '../mainapp/assets/js/persons',
        vendor: ['jquery', 'hammerjs/hammer', 'popper.js', 'leaflet/src/Leaflet', 'bootstrap/dist/js/bootstrap.js']
    },
    output: {
        path: path.resolve(__dirname, '../mainapp/assets/bundles/'),
        filename: (process.env.NODE_ENV === 'production' ? '[name]-[hash].js' : '[name].js')
    },
    devtool: 'source-map',
    resolveLoader: {
        moduleExtensions: ['-loader']
    },
    module: {
        rules: [{
            test: /\.scss$/,
            use: ExtractTextPlugin.extract({
                fallback: 'style-loader',
                //resolve-url-loader may be chained before sass-loader if necessary
                use: [{
                    loader: 'css-loader',
                    options: {
                        sourceMap: true,
                        minimize: true
                    }
                }, {
                    loader: 'resolve-url-loader',
                    options: {
                        sourceMap: true
                    }
                }, {
                    loader: 'sass-loader',
                    options: {
                        sourceMap: true
                    }
                }]
            })
        }, {
            test: /\.js$/,
            use: {
                loader: 'babel-loader',
                options: {
                    presets: ["env"],
                    sourceMap: true
                }
            }
        }, {
            test: /\.(jpe?g|gif|png)$/,
            use: 'file-loader?emitFile=false&name=[path][name].[ext]'
        }, {
            test: /\.woff(2)?(\?v=[0-9]\.[0-9]\.[0-9])?$/,
            loader: "url?limit=10000&mimetype=application/font-woff"
        }, {
            test: /\.(ttf|eot|svg)(\?v=[0-9]\.[0-9]\.[0-9])?$/,
            loader: "file"
        }
        ]
    },
    resolve: {
        alias: {
            'jquery': path.join(__dirname, '../node_modules/jquery/dist/jquery'),
        }
    },
    plugins: [
        new BundleTracker({
            path: path.resolve(__dirname, '../'),
            filename: './webpack-stats.json'
        }),
        new ExtractTextPlugin(process.env.NODE_ENV === 'production' ? 'style-[contenthash].css' : 'style.css'),
        new webpack.ProvidePlugin({
            $: "jquery",
            jQuery: "jquery",
            "Hammer": "hammerjs/hammer",
            "Popper": "popper.js"
        }),
        new webpack.optimize.CommonsChunkPlugin('vendor')
    ]
};
