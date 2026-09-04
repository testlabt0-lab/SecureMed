const fs = require('fs');
const path = require('path');

const directoryPath = path.join(__dirname, 'src');

function walk(dir, done) {
  let results = [];
  fs.readdir(dir, function(err, list) {
    if (err) return done(err);
    let i = 0;
    (function next() {
      let file = list[i++];
      if (!file) return done(null, results);
      file = path.resolve(dir, file);
      fs.stat(file, function(err, stat) {
        if (stat && stat.isDirectory()) {
          walk(file, function(err, res) {
            results = results.concat(res);
            next();
          });
        } else {
          if (file.endsWith('.tsx') || file.endsWith('.ts')) {
            results.push(file);
          }
          next();
        }
      });
    })();
  });
}

walk(directoryPath, function(err, results) {
  if (err) throw err;
  results.forEach(file => {
    let content = fs.readFileSync(file, 'utf8');
    let changed = false;

    if (content.includes('const { user } = useAuthStore();')) {
      content = content.replace(/const \{ user \} = useAuthStore\(\);/g, 'const user = useAuthStore(state => state.user);');
      changed = true;
    }
    
    if (content.includes('const { user: currentUser } = useAuthStore();')) {
      content = content.replace(/const \{ user: currentUser \} = useAuthStore\(\);/g, 'const currentUser = useAuthStore(state => state.user);');
      changed = true;
    }

    if (changed) {
      fs.writeFileSync(file, content, 'utf8');
      console.log('Updated', file);
    }
  });
});
