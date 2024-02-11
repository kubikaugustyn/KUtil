var __author__ = "kubik.augustyn@post.cz"

var a = null ?? 8
var b = 3
const c = a + b
a += 1
b ||= 9
if (c === 11) {
    for (let i = 0; i < 10; i++) {
        console.log(`I: ${i} --> C: ${c}`)
        // console.log(`I: ${i} --> C: ${c}${c}`) - test with '' template - error?
    }
} else throw SyntaxError("Bad stuff happened")


const thing = (a, b) => console.log("Hello", a, b)
const thing2 = a => console.log("Hello", a)

function hello(a) {
    // Some  massive code that would take long to parse
}
