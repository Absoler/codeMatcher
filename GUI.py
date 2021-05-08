from tkinter import *
from matchAst import *


# root = Tk()
# canvas = Canvas(root, width=200, height=180, scrollregion=(0, 0, 520, 520))  # 创建canvas
# canvas.place(x=75, y=265)  # 放置canvas的位置
# frame = Frame(canvas)  # 把frame放在canvas里
# frame.place(width=180, height=180)  # frame的长宽，和canvas差不多的
# vbar = Scrollbar(canvas, orient=VERTICAL)  # 竖直滚动条
# vbar.place(x=180, width=20, height=180)
# vbar.configure(command=canvas.yview)
# hbar = Scrollbar(canvas, orient=HORIZONTAL)  # 水平滚动条
# hbar.place(x=0, y=165, width=180, height=20)
# hbar.configure(command=canvas.xview)
# canvas.config(xscrollcommand=hbar.set, yscrollcommand=vbar.set)  # 设置
# canvas.create_window((90, 240), window=frame)  # create_window
#
# root.mainloop()

def chooseCode(event, other: Listbox, ast: Ast, infoText: Text):
    lb = event.widget
    index = (lb.curselection())[0] + 1
    node = ast.convex[index]
    infoText.delete('1.0', END)
    other.selection_clear(0, END)
    if node is None:
        return
    if node.state == Macro.PREFECT_MATCH:
        info = "完美匹配 " + node.type
        infoText.insert(END, info)
        other.selection_set(node.match[0].range[0] - 1, node.match[0].range[1] - 1)
    elif node.state == Macro.NORMAL_MATCH:
        info = "一般匹配 "+node.type+' ' + str(node.match[0].range) + '\n' + str(node.diff)
        infoText.insert(END, info)
        other.selection_set(node.match[0].range[0] - 1, node.match[0].range[1] - 1)
        print((node.match[0].range[0] - 1, node.match[0].range[1] - 1))


if __name__ == '__main__':
    oldfilename = 'old.cpp'
    newfilename = 'main.cpp'
    with open(oldfilename, 'r') as f:
        oldcodes = f.readlines()
    oldast = parse_file(oldfilename, use_cpp=False)
    oldast = Ast(oldast, oldcodes)
    with open(newfilename, 'r') as f:
        newcodes = f.readlines()
    newast = parse_file(newfilename, use_cpp=False)
    newast = Ast(newast, newcodes)
    find_perfectMatch_2(oldast, newast)
    find_normalMatch(oldast, newast)
    oldast.build_Convex()
    newast.build_Convex()

    root = Tk()
    w = 960
    h = 720
    x = (root.winfo_screenwidth() - w) / 2
    y = (root.winfo_screenheight() - h) / 2;
    root.geometry('%dx%d+%d+%d' % (w, h, x, y))

    # 存放两份代码的frame
    codeFrame = Frame(root)
    # 存放旧代码的frame
    oldFrame = Frame(codeFrame, width=w / 2, bg='Moccasin')
    oldScrollbar = Scrollbar(oldFrame, jump=1)
    oldLb = Listbox(oldFrame, yscrollcommand=oldScrollbar.set, exportselection=False)
    oldLb.pack(side=LEFT, fill=BOTH, expand=True)
    oldScrollbar.pack(side=LEFT, fill=Y)
    for i, code in enumerate(oldcodes):
        cnt = 0
        for j in range(len(code)):
            if code[j] == ' ':
                cnt += 1
            elif code[j] == '\t':
                cnt += 4
            else:
                break
        oldLb.insert(END, str(i + 1) + ' ' * (cnt + 2) + code)
    oldScrollbar.config(command=oldLb.yview)
    oldFrame.pack(side=LEFT, fill=BOTH, expand=True, padx=5, pady=5)
    # 存放新代码的frame
    newFrame = Frame(codeFrame, width=w / 2, bg='PaleGreen')
    newScrollbar = Scrollbar(newFrame, jump=1)
    newLb = Listbox(newFrame, yscrollcommand=newScrollbar.set, exportselection=False)
    newLb.pack(side=LEFT, fill=BOTH, expand=True)
    newScrollbar.pack(side=LEFT, fill=Y)
    for i, code in enumerate(newcodes):
        cnt = 0
        for j in range(len(code)):
            if code[j] == ' ':
                cnt += 1
            elif code[j] == '\t':
                cnt += 4
            else:
                break
        newLb.insert(END, str(i + 1) + ' ' * (cnt + 2) + code)
    newScrollbar.config(command=newLb.yview)
    newFrame.pack(side=RIGHT, fill=BOTH, expand=True, ipadx=5, pady=5)

    codeFrame.pack(side=TOP, fill=BOTH, expand=True)

    # 展示匹配和变更信息的Frame
    infoFrame = Frame(root)

    # matchBtn = Button(infoFrame, relief='raised')
    # matchBtn.pack(side=LEFT, fill=Y, padx=5, pady=5)
    # noneBtn = Button(infoFrame, relief='raised')
    # noneBtn.pack(side=LEFT, fill=Y, padx=5, pady=5)

    infoText = Text(infoFrame, height=10)
    infoText.pack(fill=BOTH, padx=5, pady=5)

    # matchBtn.grid(row=0, column=0)
    # noneBtn.grid(row=1, column=1)
    # infoText.grid(row=0, column=1, rowspan=2, columnspan=8)
    infoFrame.pack(side=TOP, fill=X)

    # 给旧新ListBox绑定事件
    oldLb.bind('<<ListboxSelect>>', lambda event, other=newLb, ast=oldast: chooseCode(event, other, ast, infoText))

    root.mainloop()
