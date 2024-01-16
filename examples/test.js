var __author__ = "kubik.augustyn@post.cz"

var a = 8
var b = 3
const c = a + b
if (c === 11) {
    for (let i = 0; i < 10; i++) {
        console.log(`I: ${i} --> C: ${c}`)
        // console.log(`I: ${i} --> C: ${c}${c}`) - test with '' template - error?
    }
} else throw SyntaxError("Bad stuff happened")
