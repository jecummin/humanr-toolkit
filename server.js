import express, { json } from 'express';
import {readFileSync} from 'fs';
import { createClient } from 'redis';
// import {bodyParser} from 'body-parser';

const app = express()

// connect to redis
const REDIS_PORT = parseInt(process.env.REDIS_PORT);
const REDIS_PASSWORD = process.env.REDIS_PASSWORD;
const REDIS_HOST = process.env.REDIS_HOST
const client = createClient(
    {
	socket: {
	    host: REDIS_HOST,
	    port: REDIS_PORT
	},
	REDIS_PASSWORD,
    });
client.on('error', (err) => console.log('Redis Client Error', err));
await client.connect();
console.log("Connected to redis ..");

const COMPARISON_TASK_DATABASE = process.env.COMPARISON_TASK_DATABASE;
client.select(COMPARISON_TASK_DATABASE);


// load json experiment data at server start
let comparison_tasks = JSON.parse(readFileSync('public/data/comparison_tasks.json'));
console.log("Loaded comparison tasks ...");
console.log("num tasks: ", Object.keys(comparison_tasks).length);

app.use(express.urlencoded({extended: true}));
app.use(express.json()) // To parse the incoming requests with JSON payloads

app.use(express.static('./public'));

// returns the name of the institution running the experiment
app.post('/get_name', (req, res) => {
        res.send(process.env.INSTITUTION_NAME);
})

// called by the client at the beginning of a hit
// returns the set of comparison tasks for the whole hit
app.post('/get_captions', (req, res) => {
    console.log("A worker has started a new task ...");
    console.log(req.body.taskID)
    if(req.body.taskID in comparison_tasks){
        res.send(comparison_tasks[req.body.taskID]);
    }
    else{
        res.send("");
    }
})


// called by the client after submitting each tasks
// stores the result in redis
app.post('/submit_response', (req, res) => {
    // overwrite the assignmentID, hitID, workerID with the one from the latest response
    client.hSet(req.body.taskID, "assignmentID", req.body.assignmentID);
    client.hSet(req.body.taskID, "hitID", req.body.hitID);
    client.hSet(req.body.taskID, "workerID", req.body.workerID);
    // record the response
    client.hSet(req.body.taskID, req.body.image, req.body.val);
    res.send("response recorded")
})

const COMPARISON_TASK_PORT = process.env.COMPARISON_TASK_PORT;
app.listen(COMPARISON_TASK_PORT, function() {
    console.log('server listening on port ' + COMPARISON_TASK_PORT);
});
