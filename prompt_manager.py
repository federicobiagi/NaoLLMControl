#file contenente una classe per eliminare parti di insegnamenti/esempi nel prompt ed evitare il token limit error
import re

class PromptManager():

    def __init__(self, prompt_path):
        self.path = prompt_path
    

    def find_example(self,line):
        if '"' in line and ':' in line:
            return True
        else:
            return False

    def free_space(self):
        line_num = None
        lines = []
        example_index = []
        example_regex = re.compile(r'"(.*?)" :')
        with open(self.path, 'r+') as fp:
            for l_no, line in enumerate(fp):
                lines.append(line)
                if ("A FEW EXAMPLES ON HOW YOU CAN SOLVE THE TASKS:" in line):
                    print("Line number:{}".format(l_no))
                    line_num = l_no  #line delimiting the part of examples from the rest of the instruction prompt
                    
        with open(self.path,'r+') as fp:
            for l_no,line in enumerate(fp):
                if self.find_example(line) and l_no >= line_num:
                    example_index.append(l_no)  #finds the line indices of each example start

        
        examples_to_keep = example_index[-2:]
        with open(self.path, 'r+') as fp:
            fp.truncate()
            fp.writelines(lines[:line_num+1]) #keep everything up to the examples in the file
            fp.writelines(lines[examples_to_keep[0]:]) #remove all but the last 2 examples
               
        return

       
        


if __name__ == '__main__':

    manager = PromptManager("./temp.txt")
    manager.free_space()