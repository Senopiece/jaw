// assuming envirionment `a`:

// special memory addresses:
// - 0x0: when 1 is written, the program halts
// - 0x1: stdout signal
// - 0x2: stdout trigger (reading value from there produces undefined result) (when 1 is written, writes stdout signal to the buffer, when buffer reaches 8 bits, it is printed as ascii character)
// - 0x3-0xx: the place where your program is located

// valid assumptions:
// - at the start of the program all the memory except for the `special memory addresses`` is filled with zeroes
// - at the start of the program all registers are filled with zeroes
// - the program pointer starts from 0x3

// syntax guide:
// - comment: //
// - lines are forwarded to ./augmenter {r_dec} {m_dec} {>/?} {offset_hex} {line} {*used_labels_hex_values}.
//  - offset hex is passed if `>`
//  - when there is passed argument `?` the augmenter must report with ranges of it's size and required label names in format:
//    `{min_hex}-{max_hex} {*created_labels_names} | {*used_labels_names}`,
//    `*_labels_names` is a list of label names delimited by space.
//  - when there is passed argument `>`, there will be passed additional arguments - used labels hex values (in correspondance to the used_labels returned on `?`)
//    the augmenter must report in format `{data} {*created_labels}`
//    `data` must be binary (if started with 0xb) or hexadecimal (if started with 0x)
//    `*created_labels` must be a sequence of hexadecimal numbers delimited by spaces

reg0: 0x0 = const 0x0               // reg0 must be only 0 or 1, init with 0 (this macro will actually generate no code)
reg1: 0x0 = const 0x2               // set reg1 to 2
reg2: 0x0 = const .msg              // reg2 is the data pointer
reg3: 0x0 = const .loop - .bottom   // reg3 for jmp from .bottom to .loop
reg4: 0x0 = const 0x0               // reg4 must be const 0 (this macro will actually generate no code)
reg5: 0x0 = const .halt - .top      // reg5 is for jmp from condition to halt
reg6: 0x0 = const .next             // reg6 is a condition temporal value holder
reg7: 0x0 = const .end_init         // reg7 is a condition second temporal value holder

@.loop

// check pointer reached the end, jmp to halt if so
reg2 == .msgend ? pp += reg5 (1 = reg1[1], next = reg6: @.next, end = reg7: @.end_init > @.end_end) @.top
reg7: .end_end = const .end_init

// read data bit to reg0[-1]
reg0[-1] = mem[reg2]

// stdout reg0[-1] bit
mem[reg0] = reg0[-1] // set data
mem[reg1] = 1        // trigger collect

// advance data pointer
reg2++

// jmp to loop
reg1[1] ? pp += reg3 @.bottom

@.halt
mem[reg4] = 1

@.msg
#store_ascii "Hello World!\n"
@.msgend