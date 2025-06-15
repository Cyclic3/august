# August
_FFI for Mobius_

# Usage
Just call `august.py` with a path to your script file, and it will print the generated Mobius code

# Intended development process
If you find yourself having to do anything that deviates from this sequence, you should write a bug report.

1. Write Maple code that generates the questions you want, using things like `rand(0..10)()` (without calling `randomize` or equivalents!) to create parameters.
2. Add `ASSERT` statements to ensure that the generated answers and intermediate steps are valid.
3. Append `#!export <param1>, <param2>, ...` to export those parameters to Mobius, using the transforms that are detailed below if required.
4. Prepend `#!evil_debug` to the August code.
5. Run it through `august.py`, and paste the result into the algorithm box.
6. Click `Refresh algorithm preview` a couple times to ensure the generated output makes sense, and has no errors. If there are, fix them in the August code (not the algorithm box!), add an `ASSERT` to make sure it doesn't happen again, and then repeat steps 4-5 until you are satisfied.
7. Preview the entire question a couple times, checking to make sure that the question, answer, and feedback all actually make sense and are correct. If you come across any mistakes, add an `ASSERT` if you can to ensure it doesn't happen again.
8. Replace `#!evil_debug` with `#!evil_test`. If `maple_result`'s error is not "computation exceeded the time limit", copy the `#!evil_reproduce` directive from the output box, and replace `#!evil_test` with it in the `august.py` code. This allows you to work with the broken case directly. Fix it, and then replace the `#!evil_reproduce` directive with `#!evil_debug`, and restart from step 5 (including previewing the entire question).
9. Remove all `#!evil_*` directives, run it through `august.py` one more time, and preview the whole question one final time to ensure it all works

# Script documentation
## Exports
You can export the variables `foo` and `bar` from Maple to Mobius like so:
```
#!export foo, bar
```
This will create Mobius variables `$foo` and `$bar` respectively. If you want to use the transforms (described later) `quux` then `wibble(3)` with `baz` as well, you can write:
```
#!export foo, bar, baz|quux|wibble(3)
```
## Transforms
### `latex`
This converts the value to latex
### `plot`
This emulates the behaviour of `plotmaple`, but allows the plot to be bundled with other variables, allowing you to only use one `maple` block. This will export a very long string, which you can use as a source in an image tag.

For instance, consider the following code:
```
foo := plot(x^2);
#!export foo|plot
```
This will create a `$foo` Mobius variable. In a question (or answer), you can add an image with a URL of `$foo` and alternative text describing the plot. For those who want to use the HTML editor, you can use `<img src="$foo" alt="Alt text" />` to get the same result. Be aware that not putting in alternative text will result in the image not showing up in the editor!
### `suffix`
`foo|suffix(bar)` will result in the corresponding Mobius variable being called `foo_bar`
### `dp`
`foo|dp(3)` will give a float rounded to 3 decimal places.
## Fixups
August also fixes a couple of common mistakes, such as forgetting to put `output=string` into Maple's `latex` function. It also escapes characters, allowing you to use quotes and brackets without drawing Mobius' ire.
## Evil directives
These directives can and will break everything if you leave them in. No deployed code should ever have an `#!evil_*` directive, and if it does, terrible things can and will happen. Check to nake sure none of them make it through. Please.
### `#!evil_test`
This will run the code on a loop until either Mobius times it out or an error is thrown in a loop. If you get a timeout, that means that no loop threw an error, and so you can be reasonably confident that it will not crash when presented to a student (unless your Mobius-supplied random parameters alter this behaviour!). When combined with `ASSERT`, you can end up with high confidence that questions will be valid.

When an error is reached, it will have the seed at the start of the loop appended to it, and instructions will be provided in the error to reproduce the bug.
### `#!evil_debug`
By default, August runs the code over and over until it doesn't error. In the actual assessment, this is desirable behaviour, because the worst case is exactly the same, and the best case stops coding mistakes (including failed `ASSERT`s) from giving a student an empty question.

However, this makes debugging the code rather painful. The `#!debug` directive disables this loop, and instead dumps all errors (including asserts) to the Mobius output, which will cause the script to crash and burn in a more debuggable way. If you forget to remove this before deployment, you will lose the loop protection, but everything else should run fine. Try not to forget though!

Debug mode superseeds test mode, because the other way around will just kill any question that has it left in by mistake.
### `#!evil_noassert`
This will disable `ASSERT` checking completely. This is good for debugging mathematical logic errors, but is obviously a really really bad thing in deployment. Do not deploy with this directive on.

### `#!evil_norandom`
**DO NOT USE THIS UNLESS YOU ARE 100% SURE THAT THE GENERATED MAPLE CODE WILL NOT GENERATE ANY RANDOM NUMBERS!**

This directive disables the RNG setup boilerplate, which fetches (assumed) good random numbers from Mobius. If you mess up and call the RNG after this, Maple's inbuilt (and very insecure) RNG seeding mechanism will be called. Such failures will include race conditions, where occasionally two students will be given identical questions, and may make certain questions unmarkable

There is virtually no need to use this, as the `maple` blocks have a very generous runtime constraint. As an infallible rule: if you need this, you should have already written a bug report explaining why _in detail_.

## Mobius code
We have made every effort to make sure that all of the functionality available in Mobius can be done purely with standard August, including RNG. However, it is possible that there is a feature that is not nicely implementable in Maple. If you come across such a shortcoming, please raise an issue and we'll see if we can add it!

In the meantime, Mobius code can be stored within `(*!mobius *)` blocks. For example, the (admittedly contrived code):
```
(*!mobius
    $x = 2;
*)
y := $x + 3;
#!export y
```
will output something that behaves the same as the following, albeit with a lot more boilerplate:
```
$x := 2;
$y := maple("$x + 3");
```
Be aware that each one of these splits the maple code, so if you have one anywhere else but the very beginning or very end of your script, you will end up with multiple `maple` calls. A situtation that requires this should never happen, so please raise an issue if you come across one!
