
const path = require('path');
module.exports = {
  entry: './src/index.js',
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: 'bundle.js',
    publicPath: '/'
  },
  module: {
    rules: [
      {
        test: /\.jsx?$/,
        exclude: /node_modules/,
        use: { loader: 'babel-loader', options: { presets: ['@babel/preset-react'] } }
      },
      {
        test: /\.css$/,
        use: ['style-loader','css-loader']
      }
    ]
  },
  resolve: { extensions: ['.js','.jsx'] },
  devServer: {
    static: { directory: path.join(__dirname, 'dist') },
    historyApiFallback: true,
    port: 3000,
    proxy: {
      '/api': 'http://backend:8000' // used in docker-compose
    }
  }
};
