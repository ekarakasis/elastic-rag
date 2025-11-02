# Prompt: Static Code Analysis for Memory Leak Detection

## Objective

To statically analyze a given codebase to identify potential memory leaks and resource management issues. This analysis should be performed without running the code, relying on code inspection and pattern recognition.

## Context

Please provide the following information:

*   **Programming Language**: The language the code is written in (e.g., Python, C++, Java, JavaScript).
*   **Code Snippets**: The relevant code snippets or files to be analyzed.
*   **Key Areas of Concern**: Any specific areas of the code that are suspected to be problematic.
*   **Dependencies and Frameworks**: Information about any frameworks or libraries that might have their own memory management paradigms (e.g., garbage collection, manual memory management).

## Instructions

Analyze the provided code for the following patterns and anti-patterns related to memory management:

### 1. Resource Management

*   **Unclosed Resources**: Look for resources that are opened or allocated but never closed or deallocated. This includes file handles, network connections, database connections, etc.
    *   *Example (Python)*: `f = open('file.txt')` without a corresponding `f.close()` or not using a `with` statement.
*   **Manual Memory Management (for languages like C/C++)**:
    *   Check for `malloc` or `new` without a corresponding `free` or `delete`.
    *   Verify that for every allocation, there is a clear deallocation path.

### 2. Long-Lived Objects and Collections

*   **Static Collections**: Identify any global or static collections (lists, dictionaries, arrays) that grow over time without being cleared.
*   **Caches without Eviction Policies**: Look for in-memory caches that do not have a mechanism to evict old or unused entries.
*   **Append-Only Data Structures**: Check for data structures that are only ever added to, without any mechanism for removal.

### 3. Event Listeners and Callbacks

*   **Dangling Listeners**: Identify event listeners or callbacks that are registered but never unregistered, especially on objects that have a shorter lifecycle than the event source.
    *   *Example (JavaScript)*: Adding an event listener to a DOM element that is later removed from the DOM without removing the listener.
*   **Closures Capturing Large Objects**: Look for closures (lambdas, anonymous functions) that capture references to large objects, preventing them from being garbage collected.

### 4. Circular References (in garbage-collected languages)

*   **Object-to-Object References**: Identify patterns where two or more objects reference each other, creating a cycle that the garbage collector might not be able to break (especially in older or simpler GCs).

## Output Format

Please provide the analysis in the following format:

*   **Summary**: A brief summary of the findings, including an overall assessment of the code's memory safety.
*   **Potential Issues**: A list of potential memory leaks or resource management issues, with the following details for each:
    *   **File and Line Number**: The location of the issue in the code.
    *   **Description**: A clear and concise description of the potential issue.
    *   **Severity**: An assessment of the potential impact (e.g., High, Medium, Low).
    *   **Recommendation**: A suggestion on how to fix the issue.

*   **General Recommendations**: Any general advice for improving memory management in the codebase.
