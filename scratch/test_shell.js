import Shell from 'gi://Shell';
import St from 'gi://St';
import Gio from 'gi://Gio';

console.log('Shell imported successfully:', Shell);
const tracker = Shell.WindowTracker.get_default();
console.log('WindowTracker default:', tracker);
